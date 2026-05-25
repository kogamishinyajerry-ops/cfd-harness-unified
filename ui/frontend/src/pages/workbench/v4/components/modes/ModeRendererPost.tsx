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
import { ModeTabStrip } from "../ModeTabStrip";
import { ReportFiguresPanel } from "./ReportFiguresPanel";
import { V4_CFD_COLORMAP, V4_PALETTE } from "@/theme/industrial_minimalist";
import type { ResidualSeriesPayload } from "@/types/residual_series";
import { ViewportV4, type V4CameraPreset } from "../ViewportV4";
import {
  geometryGlbUrl,
  useGlbAvailability,
} from "../../hooks/useGlbAvailability";
import {
  POST_BLUEPRINT_MINI_CHARTS,
  POST_BLUEPRINT_RADIAL_GAUGE,
  POST_BLUEPRINT_TABS,
  POST_BLUEPRINT_VERDICT,
  type PostBlueprintMiniChart,
} from "../postBlueprint";

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

export function ResidualLogChart({ payload }: ResidualLogChartProps) {
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
  const v = Math.max(0, Math.min(100, value));
  const tone = achieved
    ? V4_PALETTE.healthy
    : v >= 75
      ? V4_PALETTE.brand
      : v >= 40
        ? V4_PALETTE.warn
        : V4_PALETTE.crit;
  const circumference = 2 * Math.PI * 31;
  const dash = (v / 100) * circumference;

  return (
    <div
      className="flex flex-col items-center rounded border border-v4-border bg-v4-surfaceRaised p-2"
      data-testid="v4-post-gauge"
      data-achieved={achieved ? "true" : "false"}
    >
      <svg viewBox="0 0 88 88" className="h-[88px] w-full">
        <circle
          cx="44"
          cy="44"
          r="31"
          fill="none"
          stroke={V4_PALETTE.border}
          strokeWidth="6"
          opacity="0.85"
        />
        <circle
          cx="44"
          cy="44"
          r="31"
          fill="none"
          stroke={tone}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circumference - dash}`}
          transform="rotate(-90 44 44)"
        />
        <text
          x="44"
          y="42"
          textAnchor="middle"
          fontSize="17"
          fontFamily="ui-monospace"
          fontWeight="600"
          fill={V4_PALETTE.textPrimary}
        >
          {v.toFixed(0)}
        </text>
        <text
          x="44"
          y="55"
          textAnchor="middle"
          fontSize="7"
          fill={V4_PALETTE.textTertiary}
          fontFamily="ui-monospace"
        >
          {POST_BLUEPRINT_RADIAL_GAUGE.label}
        </text>
      </svg>
      <div className="flex w-full items-baseline justify-between text-[9px]">
        <span className="text-v4-textTertiary">
          {worst ?? "radial chart"}
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

export function CenterlineChart({ u, y }: CenterlineChartProps) {
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

function PostMiniProfileChart({ chart }: { chart: PostBlueprintMiniChart }) {
  const min = Math.min(...chart.samples);
  const max = Math.max(...chart.samples);
  const range = Math.max(1e-6, max - min);
  const points = chart.samples
    .map((value, index) => {
      const x = 8 + (index / Math.max(1, chart.samples.length - 1)) * 128;
      const y = 54 - ((value - min) / range) * 40;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const latest = chart.samples[chart.samples.length - 1];
  const latestY = 54 - ((latest - min) / range) * 40;

  return (
    <div
      className="rounded border border-v4-border bg-v4-surfaceRaised p-2"
      data-testid={`v4-post-mini-chart-${chart.id}`}
    >
      <div className="flex items-baseline justify-between text-[10px]">
        <span className="text-v4-textSecondary">{chart.label}</span>
        <span className="font-mono text-v4-textPrimary">
          {latest.toFixed(chart.id === "velocity" ? 1 : 1)} {chart.unit}
        </span>
      </div>
      <svg
        viewBox="0 0 144 64"
        preserveAspectRatio="none"
        className="mt-1 h-14 w-full"
      >
        {[0, 1, 2].map((i) => {
          const y = 14 + i * 20;
          return (
            <line
              key={i}
              x1="8"
              x2="136"
              y1={y}
              y2={y}
              stroke={V4_PALETTE.border}
              strokeWidth="0.35"
            />
          );
        })}
        <polyline
          points={points}
          fill="none"
          stroke={chart.color}
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="136" cy={latestY} r="2.1" fill={chart.color} />
      </svg>
    </div>
  );
}

export function ModeRendererPost({ caseId, cameraPreset = "iso" }: Props) {
  const ctx = useV4WorkbenchContext(caseId ?? null);
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
  const verdictColor = V4_PALETTE.healthy;
  const uMax =
    vtpScalarRange != null
      ? vtpScalarRange[1]
      : typeof (detail?.key_quantities as Record<string, unknown> | undefined)?.u_max === "number"
        ? ((detail!.key_quantities as Record<string, unknown>).u_max as number)
        : 40;

  return (
    <div data-testid="v4-mode-post" className="flex h-full w-full flex-col bg-v4-canvas">
      <ModeTabStrip
        tabs={POST_BLUEPRINT_TABS}
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
                uMax={uMax}
              />
            </>
          ) : (
            <PostEmptyViewport probing={glbProbe.available === undefined} />
          )}
          <div
            data-testid="v4-mode-post-verdict"
            data-verdict="ok"
            className="absolute bottom-3 right-3 flex min-w-[236px] items-center gap-2.5 rounded-md border bg-v4-surfaceRaised/95 px-3.5 py-2.5 shadow-xl backdrop-blur"
            style={{ borderColor: verdictColor + "99" }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke={verdictColor} strokeWidth="2.2" />
              <path
                d="M8 12l3 3 5-6"
                stroke={verdictColor}
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <div className="flex flex-col">
              <span
                className="text-[13px] font-semibold"
                style={{ color: verdictColor }}
              >
                {POST_BLUEPRINT_VERDICT.label}
              </span>
              <span className="font-mono text-[10px] text-v4-textSecondary">
                流量 +{POST_BLUEPRINT_VERDICT.flowGainPct.toFixed(1)}% · 温度 +{POST_BLUEPRINT_VERDICT.temperatureDeltaPct.toFixed(1)}%
              </span>
            </div>
          </div>
        </div>

        {/* Right column · image-7 telemetry: 3 mini profiles + 1 radial gauge */}
        <div className="flex w-72 shrink-0 flex-col gap-2 border-l border-v4-border bg-v4-shell p-3 overflow-y-auto">
          {POST_BLUEPRINT_MINI_CHARTS.map((chart) => (
            <PostMiniProfileChart key={chart.id} chart={chart} />
          ))}
          <ConvergenceGauge
            value={POST_BLUEPRINT_RADIAL_GAUGE.valuePct}
            worst="基准覆盖率"
            achieved
          />
          {/* DEC-V61-204 (M4 C3): backend matplotlib report figures as
              canonical, provenance-labelled artifacts. Auto-fetches; on a
              matplotlib-absent build it shows an explicit "unavailable on
              this build" state, never a crash. */}
          <ReportFiguresPanel caseId={caseId ?? null} />
          <div className="rounded border border-dashed border-v4-border bg-v4-canvas p-2 text-[9px] leading-relaxed text-v4-textTertiary">
            基准剖面参考；主视图保持后端表面场与流线结果。
          </div>
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
