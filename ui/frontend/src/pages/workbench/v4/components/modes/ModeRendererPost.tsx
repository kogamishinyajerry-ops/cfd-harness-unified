/**
 * V4 · Mode renderer · 后处理 (Post) · per UI-SPEC §4.7 · R6 wired.
 *
 * Real run telemetry from useV4WorkbenchContext.successfulRunDetail
 * plus structured residual time-series from useResidualSeries (R6).
 *
 * Right column composition:
 *   1. Task spec chips (Re / geometry_type / flow_type / steady_state)
 *   2. **Multi-series residual log-decay chart** — Ux / Uy / Uz / p
 *      with stable colors keyed off V4_CFD_COLORMAP. Source label
 *      below the chart distinguishes log-parsed (true iteration
 *      series) from run-history (point-per-run multi-run series).
 *      Empty / error states render explicit placeholders, never mock.
 *   3. **Real convergence gauge** derived from worst-case residual ÷
 *      target_floor (computed in useResidualSeries.convergenceGauge…).
 *   4. Centerline profile chart (u(y) from key_quantities) kept as
 *      a co-equal profile slot — multi-profile expansion when more
 *      arrays are present (currently only u_centerline for LDC).
 *   5. Verdict pill (success/fail tied to run) anchored on scene.
 *   6. Scalar key_quantities table (filtered to numbers only).
 *
 * Source-mode UX (R6 acceptance bar):
 *   - source="log"   → "解析自 log.simpleFoam · N 迭代"
 *   - source="runs"  → "多 run 终值序列 · N 次运行"
 *   - source="empty" → "无运行历史 · 等待求解"
 *   - error          → "残差序列加载失败 · 重试"
 */
import { useState } from "react";

import { useV4WorkbenchContext } from "../../hooks/useV4WorkbenchContext";
import {
  convergenceGaugeFromSeries,
  useResidualSeries,
} from "../../hooks/useResidualSeries";
import { ModeTabStrip } from "../ModeTabStrip";
import { V4_CFD_COLORMAP, V4_PALETTE } from "@/theme/industrial_minimalist";
import type { ResidualSeriesPayload } from "@/types/residual_series";
import { ViewportV4, type V4CameraPreset } from "../ViewportV4";
import {
  geometryGlbUrl,
  useGlbAvailability,
} from "../../hooks/useGlbAvailability";

interface Props {
  caseId?: string;
  cameraPreset?: V4CameraPreset;
}

function fmtSci(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return n.toExponential(2);
}

function fmtNum(n: number | null | undefined, digits = 3): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return n.toFixed(digits);
}

/** Stable color assignment for the residual chart legend. Frontends
 *  must keep these consistent across renders (Codex R6 acceptance:
 *  "stable colors/legend") so a user toggling series or switching cases
 *  doesn't get a shuffled palette. */
const RESIDUAL_COLOR: Record<string, string> = {
  Ux: V4_CFD_COLORMAP[0], // deep blue
  Uy: V4_CFD_COLORMAP[1], // cyan
  Uz: V4_CFD_COLORMAP[2], // green
  p: V4_CFD_COLORMAP[4], // orange
  k: V4_CFD_COLORMAP[3], // yellow
  omega: V4_CFD_COLORMAP[5], // red
  epsilon: V4_CFD_COLORMAP[5],
  T: V4_PALETTE.warn,
};

function residualColor(name: string): string {
  return RESIDUAL_COLOR[name] ?? V4_PALETTE.brand;
}

/** Canonical legend order. Codex R6 L-1 closure: the chart legend
 *  must render in a stable sequence across cases so the user's eye
 *  doesn't have to relearn the mapping when the data shape changes.
 *  Keys not in this list fall through to the end in alphabetical
 *  order. Mirrors the CFD convention U-first → p → turbulence → scalars.
 *  Exported for R8 unit-test pinning (canonicalSeriesEntries.test.ts). */
export const CANONICAL_ORDER: readonly string[] = [
  "Ux",
  "Uy",
  "Uz",
  "p",
  "k",
  "omega",
  "epsilon",
  "T",
];

export function canonicalSeriesEntries<T>(
  series: Record<string, T>,
): Array<[string, T]> {
  const entries = Object.entries(series);
  return entries.sort(([a], [b]) => {
    const ai = CANONICAL_ORDER.indexOf(a);
    const bi = CANONICAL_ORDER.indexOf(b);
    if (ai >= 0 && bi >= 0) return ai - bi;
    if (ai >= 0) return -1;
    if (bi >= 0) return 1;
    return a.localeCompare(b);
  });
}

interface ResidualLogChartProps {
  payload: ResidualSeriesPayload;
}

function ResidualLogChart({ payload }: ResidualLogChartProps) {
  const seriesEntries = canonicalSeriesEntries(payload.series).filter(
    ([, points]) => points.length > 0,
  );
  if (seriesEntries.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center rounded border border-dashed border-v4-border bg-v4-canvas text-[11px] text-v4-textTertiary">
        无残差数据
      </div>
    );
  }

  // x bounds: from min x across all series to max x.
  let xMin = Infinity;
  let xMax = -Infinity;
  for (const [, pts] of seriesEntries) {
    for (const p of pts) {
      if (p.x < xMin) xMin = p.x;
      if (p.x > xMax) xMax = p.x;
    }
  }
  const xSpan = Math.max(1e-9, xMax - xMin);

  // y bounds: from log-floor (target_floor / 10) to max log10 across data.
  const logFloor = Math.log10(Math.max(1e-12, payload.target_floor / 10));
  let logMax = Math.log10(Math.max(1e-12, payload.target_floor));
  for (const [, pts] of seriesEntries) {
    for (const p of pts) {
      if (p.y > 0) {
        const lp = Math.log10(p.y);
        if (lp > logMax) logMax = lp;
      }
    }
  }
  const logSpan = Math.max(1, logMax - logFloor);

  const W = 200;
  const H = 120;
  const PAD_L = 22;
  const PAD_R = 6;
  const PAD_T = 8;
  const PAD_B = 16;
  const innerW = W - PAD_L - PAD_R;
  const innerH = H - PAD_T - PAD_B;

  const sx = (x: number) => PAD_L + ((x - xMin) / xSpan) * innerW;
  const sy = (y: number) => {
    const ly = Math.log10(Math.max(1e-30, y));
    return PAD_T + (1 - (ly - logFloor) / logSpan) * innerH;
  };

  // Decade gridlines.
  const decades: number[] = [];
  for (let d = Math.ceil(logFloor); d <= Math.floor(logMax); d++) {
    decades.push(d);
  }

  // Target-floor reference line.
  const targetY = sy(payload.target_floor);

  return (
    <div className="flex flex-col gap-1">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        className="h-32 w-full"
        data-testid="v4-post-residual-chart"
      >
        {/* Gridlines */}
        {decades.map((d) => {
          const y = sy(Math.pow(10, d));
          return (
            <g key={d}>
              <line
                x1={PAD_L}
                y1={y}
                x2={W - PAD_R}
                y2={y}
                stroke={V4_PALETTE.border}
                strokeWidth="0.4"
                opacity="0.55"
              />
              <text
                x={PAD_L - 2}
                y={y + 2}
                textAnchor="end"
                fontSize="6"
                fill={V4_PALETTE.textTertiary}
                fontFamily="ui-monospace"
              >
                {d >= 0 ? `1e+${d}` : `1e${d}`}
              </text>
            </g>
          );
        })}
        {/* Axes */}
        <line
          x1={PAD_L}
          y1={PAD_T}
          x2={PAD_L}
          y2={H - PAD_B}
          stroke={V4_PALETTE.border}
          strokeWidth="0.6"
        />
        <line
          x1={PAD_L}
          y1={H - PAD_B}
          x2={W - PAD_R}
          y2={H - PAD_B}
          stroke={V4_PALETTE.border}
          strokeWidth="0.6"
        />
        {/* Target-floor line */}
        <line
          x1={PAD_L}
          y1={targetY}
          x2={W - PAD_R}
          y2={targetY}
          stroke={V4_PALETTE.healthy}
          strokeWidth="0.6"
          strokeDasharray="3 2"
          opacity="0.8"
        />
        {/* Series lines */}
        {seriesEntries.map(([name, pts]) => {
          const color = residualColor(name);
          if (pts.length === 1) {
            const p = pts[0];
            return (
              <circle
                key={name}
                cx={sx(p.x)}
                cy={sy(p.y)}
                r={2}
                fill={color}
              />
            );
          }
          const path = pts
            .map((p, i) => `${i === 0 ? "M" : "L"} ${sx(p.x).toFixed(2)} ${sy(p.y).toFixed(2)}`)
            .join(" ");
          return (
            <g key={name}>
              <path
                d={path}
                fill="none"
                stroke={color}
                strokeWidth="1.4"
                strokeLinejoin="round"
                strokeLinecap="round"
              />
              {pts.map((p, i) => (
                <circle
                  key={i}
                  cx={sx(p.x)}
                  cy={sy(p.y)}
                  r={1.4}
                  fill={color}
                />
              ))}
            </g>
          );
        })}
        {/* x-axis labels at ends */}
        <text
          x={PAD_L}
          y={H - 4}
          textAnchor="start"
          fontSize="6"
          fill={V4_PALETTE.textTertiary}
          fontFamily="ui-monospace"
        >
          {xMin.toFixed(0)}
        </text>
        <text
          x={W - PAD_R}
          y={H - 4}
          textAnchor="end"
          fontSize="6"
          fill={V4_PALETTE.textTertiary}
          fontFamily="ui-monospace"
        >
          {xMax.toFixed(0)}
        </text>
      </svg>
      {/* Legend · stable color order */}
      <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[9px]">
        {seriesEntries.map(([name, pts]) => {
          const last = pts[pts.length - 1];
          return (
            <span
              key={name}
              className="inline-flex items-center gap-1 font-mono"
              data-testid={`v4-post-residual-legend-${name}`}
            >
              <span
                aria-hidden
                className="h-1.5 w-3 rounded-sm"
                style={{ backgroundColor: residualColor(name) }}
              />
              <span className="text-v4-textPrimary">{name}</span>
              <span className="text-v4-textTertiary">
                {fmtSci(last?.y)}
              </span>
            </span>
          );
        })}
      </div>
    </div>
  );
}

interface ConvergenceGaugeProps {
  value: number;
  worst: string | null;
  achieved: boolean;
}

function ConvergenceGauge({ value, worst, achieved }: ConvergenceGaugeProps) {
  // Semicircle dial · 0..100% along arc.
  const SIZE = 88;
  const cx = SIZE / 2;
  const cy = SIZE - 14;
  const r = 32;
  const startAngle = Math.PI; // 180°
  const endAngle = 0; // 0°
  const v = Math.max(0, Math.min(100, value));
  const angle = startAngle - (v / 100) * (startAngle - endAngle);
  const tipX = cx + r * Math.cos(angle);
  const tipY = cy - r * Math.sin(angle);

  const tone = achieved
    ? V4_PALETTE.healthy
    : v >= 75
      ? V4_PALETTE.brand
      : v >= 40
        ? V4_PALETTE.warn
        : V4_PALETTE.crit;

  return (
    <div
      className="flex flex-col items-center rounded border border-v4-border bg-v4-surfaceRaised p-2"
      data-testid="v4-post-gauge"
      data-achieved={achieved ? "true" : "false"}
    >
      <svg viewBox={`0 0 ${SIZE} ${SIZE - 8}`} className="h-16 w-full">
        {/* Background arc */}
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none"
          stroke={V4_PALETTE.border}
          strokeWidth="3"
          strokeLinecap="round"
        />
        {/* Threshold ticks at 25 / 50 / 75 */}
        {[25, 50, 75].map((t) => {
          const a = startAngle - (t / 100) * (startAngle - endAngle);
          const x1 = cx + (r - 4) * Math.cos(a);
          const y1 = cy - (r - 4) * Math.sin(a);
          const x2 = cx + (r + 2) * Math.cos(a);
          const y2 = cy - (r + 2) * Math.sin(a);
          return (
            <line
              key={t}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke={V4_PALETTE.textTertiary}
              strokeWidth="0.5"
            />
          );
        })}
        {/* Filled arc to value */}
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${tipX} ${tipY}`}
          fill="none"
          stroke={tone}
          strokeWidth="3"
          strokeLinecap="round"
        />
        {/* Center text */}
        <text
          x={cx}
          y={cy - 4}
          textAnchor="middle"
          fontSize="14"
          fontFamily="ui-monospace"
          fontWeight="600"
          fill={V4_PALETTE.textPrimary}
        >
          {v.toFixed(0)}
        </text>
        <text
          x={cx}
          y={cy + 6}
          textAnchor="middle"
          fontSize="6"
          fill={V4_PALETTE.textTertiary}
          fontFamily="ui-monospace"
        >
          % CONVERGED
        </text>
      </svg>
      <div className="mt-0.5 flex w-full items-baseline justify-between text-[9px]">
        <span className="text-v4-textTertiary">
          {worst ? `bottleneck · ${worst}` : "—"}
        </span>
        <span
          className="font-mono"
          style={{ color: tone }}
          data-testid="v4-post-gauge-status"
        >
          {achieved ? "已收敛" : v >= 75 ? "接近" : v >= 40 ? "进展中" : "未收敛"}
        </span>
      </div>
    </div>
  );
}

interface CenterlineChartProps {
  u: number[];
  y: number[];
}

function CenterlineChart({ u, y }: CenterlineChartProps) {
  if (u.length === 0 || y.length === 0 || u.length !== y.length) {
    return (
      <div className="flex h-full w-full items-center justify-center rounded border border-dashed border-v4-border bg-v4-surfaceRaised/40 text-[11px] text-v4-textTertiary">
        无 centerline 数据
      </div>
    );
  }
  const uMin = Math.min(...u);
  const uMax = Math.max(...u);
  const yMin = Math.min(...y);
  const yMax = Math.max(...y);
  const uRange = Math.max(1e-9, uMax - uMin);
  const yRange = Math.max(1e-9, yMax - yMin);
  const sx = (v: number) => 12 + ((v - uMin) / uRange) * 76;
  const sy = (v: number) => 88 - ((v - yMin) / yRange) * 76;
  const path = u.map((v, i) => `${sx(v).toFixed(2)},${sy(y[i]).toFixed(2)}`).join(" ");
  const zeroX = uMin < 0 && uMax > 0 ? sx(0) : null;
  return (
    <svg
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      className="h-full w-full"
      data-testid="v4-post-centerline-chart"
    >
      <line x1="12" y1="88" x2="88" y2="88" stroke={V4_PALETTE.border} strokeWidth="0.5" />
      <line x1="12" y1="12" x2="12" y2="88" stroke={V4_PALETTE.border} strokeWidth="0.5" />
      {zeroX != null && (
        <line
          x1={zeroX}
          y1="12"
          x2={zeroX}
          y2="88"
          stroke={V4_PALETTE.textTertiary}
          strokeWidth="0.4"
          strokeDasharray="2 2"
          opacity="0.5"
        />
      )}
      <polyline
        points={`12,${sy(y[0]).toFixed(2)} ${path} 12,${sy(y[y.length - 1]).toFixed(2)}`}
        fill={V4_PALETTE.brand}
        opacity="0.12"
      />
      <polyline points={path} fill="none" stroke={V4_PALETTE.brand} strokeWidth="1.2" />
      {u.map((v, i) => (
        <circle
          key={i}
          cx={sx(v)}
          cy={sy(y[i])}
          r="0.9"
          fill={V4_PALETTE.active}
        />
      ))}
      <text x="50" y="98" textAnchor="middle" fontSize="3.5" fill={V4_PALETTE.textTertiary} fontFamily="ui-monospace">
        u · {fmtNum(uMin, 2)} → {fmtNum(uMax, 2)}
      </text>
      <text
        x="3"
        y="50"
        textAnchor="middle"
        fontSize="3.5"
        fill={V4_PALETTE.textTertiary}
        fontFamily="ui-monospace"
        transform="rotate(-90 3 50)"
      >
        y · {fmtNum(yMin, 2)} → {fmtNum(yMax, 2)}
      </text>
    </svg>
  );
}

/** Legend strip rendered along the bottom of the Post viewport · honest
 *  placeholder until real U-colored surface.glb lands (B2.5).
 *  Reads the runtime velocity range from key_quantities when available;
 *  falls back to [0, 1] normalized. */
function VelocityLegendStrip({ uMax }: { uMax: number | null }) {
  return (
    <div
      className="absolute bottom-3 left-1/2 z-10 -translate-x-1/2 rounded-md border border-v4-border bg-v4-shell/85 px-2 py-1 text-[9px] backdrop-blur"
      data-testid="v4-post-velocity-legend"
    >
      <div className="flex items-center gap-2">
        <span className="font-mono text-v4-textTertiary">|U|</span>
        <div
          className="h-2 w-32 rounded"
          style={{
            background: `linear-gradient(to right, ${V4_CFD_COLORMAP.join(", ")})`,
          }}
        />
        <span className="font-mono text-v4-textPrimary">
          0 → {uMax != null ? uMax.toFixed(2) : "—"} m/s
        </span>
      </div>
    </div>
  );
}

export function ModeRendererPost({ caseId, cameraPreset = "iso" }: Props) {
  const ctx = useV4WorkbenchContext(caseId ?? null);
  const residuals = useResidualSeries(caseId ?? null);
  const glbUrl = geometryGlbUrl(caseId ?? null);
  const glbProbe = useGlbAvailability(glbUrl);
  const hasGeom = glbProbe.available === true;

  // B2.5 · VTP overlay URLs · backend endpoints serve real foamToVTK
  // output. When unavailable (no solver run yet), the kernel attach
  // silently fails and the base glb keeps rendering — graceful degrade.
  const surfaceVtpUrl = caseId
    ? `/api/cases/${encodeURIComponent(caseId)}/post/surface.vtp?patch=engine`
    : null;
  const streamlinesVtpUrl = caseId
    ? `/api/cases/${encodeURIComponent(caseId)}/post/streamlines.vtp`
    : null;
  const [vtpScalarRange, setVtpScalarRange] =
    useState<[number, number] | null>(null);
  const detail = ctx.successfulRunDetail ?? ctx.runDetail;
  const showingFallbackRun =
    ctx.successfulRunDetail != null &&
    ctx.latestRun?.run_id !== ctx.latestSuccessfulRun?.run_id;
  const success = detail?.success;
  const verdict: "ok" | "fail" | "pending" = success === true
    ? "ok"
    : detail
      ? "fail"
      : "pending";

  const kq = (detail?.key_quantities ?? {}) as Record<string, unknown>;
  const uCenterline = Array.isArray(kq.u_centerline)
    ? (kq.u_centerline as unknown[]).filter(
        (v): v is number => typeof v === "number" && Number.isFinite(v),
      )
    : [];
  const yCenterline = Array.isArray(kq.u_centerline_y)
    ? (kq.u_centerline_y as unknown[]).filter(
        (v): v is number => typeof v === "number" && Number.isFinite(v),
      )
    : [];

  const scalarKq = Object.entries(kq).filter(
    ([, v]) => typeof v === "number" && Number.isFinite(v as number),
  );

  const taskSpec = (detail?.task_spec ?? {}) as Record<string, unknown>;
  const taskChips = Object.entries(taskSpec)
    .filter(([k]) => k !== "name")
    .slice(0, 4);

  const verdictColor =
    verdict === "ok"
      ? V4_PALETTE.healthy
      : verdict === "fail"
        ? V4_PALETTE.crit
        : V4_PALETTE.textTertiary;
  const verdictLabel =
    verdict === "ok" ? "通过" : verdict === "fail" ? "未通过" : "—";

  const gauge = convergenceGaugeFromSeries(residuals.data);
  const sourceLabel =
    residuals.data == null
      ? residuals.isLoading
        ? "加载残差…"
        : residuals.error
          ? "残差序列加载失败"
          : "残差序列待加载"
      : residuals.data.source === "log"
        ? `解析 log · ${residuals.data.sample_count} 迭代`
        : residuals.data.source === "runs"
          ? `多 run 终值 · ${residuals.data.sample_count} 次`
          : "无运行历史";

  return (
    <div data-testid="v4-mode-post" className="flex h-full w-full flex-col bg-v4-canvas">
      <ModeTabStrip
        tabs={[
          { id: "pv", label: "逐层 PV" },
          { id: "iso", label: "等值面" },
          { id: "analysis", label: "分析" },
          { id: "video", label: "视频" },
          { id: "render", label: "渲染" },
        ]}
        activeTabId="pv"
        trailing={
          <span className="font-mono text-[10px]">
            {detail?.run_id ?? "—"} · {fmtNum(detail?.duration_s, 1)}s
            {showingFallbackRun && (
              <span className="ml-1 text-v4-warn">· 历史成功</span>
            )}
          </span>
        }
      />

      <div className="flex min-h-0 flex-1">
        {/* Scene · ~60% · 2026-05-19 dogfood retrofit:
            Previously this was IndustrialBoxScene + hand-drawn
            StreamlineField + a static colorbar — ZERO real data.
            Now: real case geometry via ViewportV4(glb). U-colored
            surface + integrated streamlines are B2.5 (needs new
            backend exporter); the bottom legend is a labeled
            placeholder reading the run's u_max when present. */}
        <div className="relative flex min-h-0 flex-[1.4] items-center justify-center">
          {hasGeom && glbUrl ? (
            <>
              <ViewportV4
                glbUrl={glbUrl}
                cameraPreset={cameraPreset}
                surfaceVtpUrl={surfaceVtpUrl}
                streamlinesVtpUrl={streamlinesVtpUrl}
                onVtpRangeReady={setVtpScalarRange}
              />
              {/* Velocity legend prefers the VTP scalar range (real U
                  magnitude from foamToVTK) over the run's key_quantities
                  u_max, which is the bulk-flow average and undersells
                  the field maxima. Fall back gracefully when neither
                  is present. */}
              <VelocityLegendStrip
                uMax={
                  vtpScalarRange != null
                    ? vtpScalarRange[1]
                    : typeof (detail?.key_quantities as Record<string, unknown> | undefined)?.u_max === "number"
                      ? ((detail!.key_quantities as Record<string, unknown>).u_max as number)
                      : null
                }
              />
            </>
          ) : (
            <PostEmptyViewport probing={glbProbe.available === undefined} />
          )}
          <div
            data-testid="v4-mode-post-verdict"
            data-verdict={verdict}
            className="absolute bottom-3 right-3 flex items-center gap-2.5 rounded-md border bg-v4-canvas/95 px-3 py-2 shadow-lg"
            style={{ borderColor: verdictColor + "99" }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke={verdictColor} strokeWidth="2.2" />
              {verdict === "ok" && (
                <path
                  d="M8 12l3 3 5-6"
                  stroke={verdictColor}
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              )}
              {verdict === "fail" && (
                <path
                  d="M8 8l8 8M16 8l-8 8"
                  stroke={verdictColor}
                  strokeWidth="2.2"
                  strokeLinecap="round"
                />
              )}
            </svg>
            <div className="flex flex-col">
              <span
                className="text-[12px] font-semibold"
                style={{ color: verdictColor }}
              >
                {verdictLabel} · 算例验收
              </span>
              <span className="text-[10px] text-v4-textSecondary">
                {detail?.verdict_summary ?? "等待运行结果"}
              </span>
            </div>
          </div>
        </div>

        {/* Right column · history + gauge + centerline + KQ */}
        <div className="flex w-72 shrink-0 flex-col gap-2 border-l border-v4-border bg-v4-shell p-3 overflow-y-auto">
          {/* Task spec chips */}
          <div className="flex flex-wrap gap-1">
            {taskChips.map(([k, v]) => (
              <span
                key={k}
                className="rounded border border-v4-border bg-v4-surfaceRaised px-1.5 py-0.5 font-mono text-[9px] text-v4-textSecondary"
                title={k}
              >
                <span className="text-v4-textTertiary">{k}</span>={" "}
                <span className="text-v4-textPrimary">{String(v)}</span>
              </span>
            ))}
          </div>

          {/* R6 · Multi-series residual log chart */}
          <div className="flex flex-col gap-1 rounded border border-v4-border bg-v4-surfaceRaised p-2">
            <div className="flex items-baseline justify-between text-[10px]">
              <span className="text-v4-textSecondary">残差衰减 · log10</span>
              <span
                className="font-mono text-v4-textTertiary"
                data-testid="v4-post-residual-source"
                data-source={residuals.data?.source ?? "unknown"}
              >
                {sourceLabel}
              </span>
            </div>
            {residuals.isLoading && !residuals.data && (
              <div className="flex h-32 items-center justify-center text-[11px] text-v4-textTertiary">
                加载残差序列…
              </div>
            )}
            {residuals.error && (
              <div className="flex h-32 items-center justify-center text-[11px] text-v4-crit">
                残差序列加载失败
              </div>
            )}
            {residuals.data && residuals.data.source === "empty" && (
              <div className="flex h-32 items-center justify-center rounded border border-dashed border-v4-border bg-v4-canvas text-[11px] text-v4-textTertiary">
                {residuals.data.note}
              </div>
            )}
            {residuals.data && residuals.data.source !== "empty" && (
              <ResidualLogChart payload={residuals.data} />
            )}
          </div>

          {/* R6 · Real convergence gauge */}
          <ConvergenceGauge {...gauge} />

          {/* Centerline profile chart */}
          <div className="flex flex-col gap-1 rounded border border-v4-border bg-v4-surfaceRaised p-2">
            <div className="flex items-baseline justify-between text-[10px]">
              <span className="text-v4-textSecondary">中线速度剖面 u(y)</span>
              <span className="font-mono text-v4-textTertiary">
                {uCenterline.length} 点
              </span>
            </div>
            <div className="h-32 w-full">
              <CenterlineChart u={uCenterline} y={yCenterline} />
            </div>
          </div>

          {/* Key quantities table */}
          {scalarKq.length > 0 && (
            <div className="flex flex-col gap-1 rounded border border-v4-border bg-v4-surfaceRaised p-2">
              <div className="text-[10px] text-v4-textSecondary">关键量</div>
              <ul className="space-y-0.5 text-[10px]">
                {scalarKq.map(([k, v]) => (
                  <li
                    key={k}
                    className="flex items-baseline justify-between gap-2"
                  >
                    <span className="truncate text-v4-textTertiary" title={k}>
                      {k}
                    </span>
                    <span className="font-mono text-v4-textPrimary">
                      {fmtSci(v as number)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {!detail && (
            <div className="flex flex-1 items-center justify-center rounded border border-dashed border-v4-border bg-v4-surfaceRaised/40 px-3 py-6 text-center text-[11px] text-v4-textTertiary">
              {caseId ? "等待运行结果" : "未选择算例"}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/** Honest empty state when the case has no geometry uploaded yet.
 *  Replaces the SVG cartoon fallback for the pre-import situation. */
function PostEmptyViewport({ probing }: { probing: boolean }) {
  return (
    <div
      data-testid="v4-post-empty-viewport"
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
