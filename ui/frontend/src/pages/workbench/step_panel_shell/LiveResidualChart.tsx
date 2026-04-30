// Phase-1A live residual chart (DEC-V61-097).
//
// Subscribes to the SolveStream context, renders a log-scale SVG
// line chart that updates in real time as icoFoam emits residuals.
// Replaces the static residual-history.png viewport for Step 4 with
// a streaming view — no more "wait 60s, then see what happened".

import { useMemo } from "react";

import { useSolveStream } from "./SolveStreamContext";

interface LiveResidualChartProps {
  caseId: string;
  height: number;
}

const _W = 720;
const _PAD_L = 56;
const _PAD_R = 130;
const _PAD_T = 28;
const _PAD_B = 36;

const _COLORS = {
  Ux: "#60a5fa", // blue
  Uy: "#facc15", // amber
  Uz: "#a78bfa", // violet
  p: "#34d399", // emerald
};

export function LiveResidualChart({ caseId: _caseId, height }: LiveResidualChartProps) {
  const { series, phase, errorMessage, summary } = useSolveStream();

  const { plotW, plotH, xMax, yMinLog, yMaxLog, polylines, singletons } = useMemo(() => {
    const plotW = _W - _PAD_L - _PAD_R;
    const plotH = height - _PAD_T - _PAD_B;
    if (series.length === 0) {
      return {
        plotW,
        plotH,
        xMax: 1,
        yMinLog: -3,
        yMaxLog: 0,
        polylines: { p: "", Ux: "", Uy: "", Uz: "" },
        singletons: { p: null, Ux: null, Uy: null, Uz: null },
      };
    }
    const xMax = series[series.length - 1].t || 1;
    // Find log-range across all visible residuals.
    const allVals: number[] = [];
    for (const row of series) {
      for (const k of ["p", "Ux", "Uy", "Uz"] as const) {
        const v = row[k];
        if (v !== undefined && v > 0) allVals.push(v);
      }
    }
    const safeLog10 = (x: number) => Math.log10(Math.max(x, 1e-12));
    const yMinLog = allVals.length
      ? Math.floor(safeLog10(Math.min(...allVals)))
      : -6;
    const yMaxLog = allVals.length
      ? Math.ceil(safeLog10(Math.max(...allVals)))
      : 0;
    const yLogSpan = Math.max(yMaxLog - yMinLog, 1);

    const buildSeries = (key: "p" | "Ux" | "Uy" | "Uz") => {
      const coords: { px: number; py: number }[] = [];
      for (const row of series) {
        const v = row[key];
        if (v === undefined || v <= 0) continue;
        const xFrac = row.t / xMax;
        const yFrac = (safeLog10(v) - yMinLog) / yLogSpan;
        coords.push({
          px: _PAD_L + xFrac * plotW,
          py: _PAD_T + (1 - yFrac) * plotH,
        });
      }
      const path =
        coords.length >= 2
          ? `M ${coords
              .map((c) => `${c.px.toFixed(1)},${c.py.toFixed(1)}`)
              .join(" L ")}`
          : "";
      // Codex 45960a1 round-10 P2-a: when a field has only ONE
      // iterative residual (e.g. one early step then everything
      // diagonal), the polyline path is empty (needs ≥2 points)
      // and the chart shows nothing. Surface the singleton as a
      // marker so the user still sees the measurement.
      const singleton = coords.length === 1 ? coords[0] : null;
      return { path, singleton };
    };

    const seriesP = buildSeries("p");
    const seriesUx = buildSeries("Ux");
    const seriesUy = buildSeries("Uy");
    const seriesUz = buildSeries("Uz");

    return {
      plotW,
      plotH,
      xMax,
      yMinLog,
      yMaxLog,
      polylines: {
        p: seriesP.path,
        Ux: seriesUx.path,
        Uy: seriesUy.path,
        Uz: seriesUz.path,
      },
      singletons: {
        p: seriesP.singleton,
        Ux: seriesUx.singleton,
        Uy: seriesUy.singleton,
        Uz: seriesUz.singleton,
      },
    };
  }, [series, height]);

  const yLogSpan = Math.max(yMaxLog - yMinLog, 1);

  // Y gridlines: one per integer log decade.
  const yTicks: { logY: number; py: number }[] = [];
  for (let logY = Math.ceil(yMinLog); logY <= Math.floor(yMaxLog); logY++) {
    const yFrac = (logY - yMinLog) / yLogSpan;
    yTicks.push({ logY, py: _PAD_T + (1 - yFrac) * plotH });
  }

  // X gridlines: 5 evenly spaced.
  const xTicks: { t: number; px: number }[] = [];
  for (let i = 0; i <= 5; i++) {
    const f = i / 5;
    xTicks.push({ t: f * xMax, px: _PAD_L + f * plotW });
  }

  const lastRow = series[series.length - 1];
  const progressPct = xMax > 0 ? Math.min(100, (lastRow?.t ?? 0) / 2.0 * 100) : 0;

  return (
    <div
      data-testid="live-residual-chart"
      className="rounded-md border border-surface-800 bg-surface-950/60 p-3"
    >
      <div className="mb-2 flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-surface-500">
        <span>Live residuals · icoFoam</span>
        <span data-testid="live-residual-phase">
          {phase === "idle" && "idle"}
          {phase === "streaming" && (
            <span className="text-amber-300">
              streaming · t={lastRow?.t.toFixed(3) ?? "0.000"}s · {progressPct.toFixed(0)}%
            </span>
          )}
          {phase === "completed" && (
            <span className={summary?.converged ? "text-emerald-300" : "text-amber-300"}>
              {summary?.converged ? "converged ✓" : "completed"}
            </span>
          )}
          {phase === "error" && <span className="text-rose-300">error</span>}
        </span>
      </div>

      <svg
        viewBox={`0 0 ${_W} ${height}`}
        width="100%"
        height={height}
        style={{ background: "rgb(12,14,22)" }}
      >
        {/* Axis box */}
        <rect
          x={_PAD_L}
          y={_PAD_T}
          width={plotW}
          height={plotH}
          fill="none"
          stroke="rgba(160,165,180,0.7)"
          strokeWidth="1"
        />

        {/* Y gridlines + labels (decades) */}
        {yTicks.map(({ logY, py }) => (
          <g key={`y-${logY}`}>
            <line
              x1={_PAD_L}
              y1={py}
              x2={_PAD_L + plotW}
              y2={py}
              stroke="rgba(60,64,76,0.6)"
              strokeWidth="1"
            />
            <text
              x={_PAD_L - 6}
              y={py + 3}
              fontSize="9"
              textAnchor="end"
              fill="rgb(220,225,235)"
            >
              1e{logY >= 0 ? `+${logY}` : logY}
            </text>
          </g>
        ))}

        {/* X gridlines + tick labels */}
        {xTicks.map(({ t, px }) => (
          <g key={`x-${t.toFixed(3)}`}>
            <line
              x1={px}
              y1={_PAD_T}
              x2={px}
              y2={_PAD_T + plotH}
              stroke="rgba(60,64,76,0.6)"
              strokeWidth="1"
            />
            <text
              x={px}
              y={_PAD_T + plotH + 14}
              fontSize="9"
              textAnchor="middle"
              fill="rgb(220,225,235)"
            >
              {t.toFixed(2)}
            </text>
          </g>
        ))}

        {/* Axis labels */}
        <text
          x={_PAD_L + plotW / 2}
          y={height - 6}
          fontSize="10"
          textAnchor="middle"
          fill="rgb(220,225,235)"
        >
          time t (s)
        </text>
        <text
          x={4}
          y={_PAD_T - 6}
          fontSize="10"
          fill="rgb(220,225,235)"
        >
          Initial residual (log)
        </text>

        {/* Series polylines */}
        {polylines.Ux && (
          <path
            data-testid="live-residual-Ux"
            d={polylines.Ux}
            stroke={_COLORS.Ux}
            strokeWidth="1.5"
            fill="none"
          />
        )}
        {polylines.Uy && (
          <path
            data-testid="live-residual-Uy"
            d={polylines.Uy}
            stroke={_COLORS.Uy}
            strokeWidth="1.5"
            fill="none"
          />
        )}
        {polylines.Uz && (
          <path
            data-testid="live-residual-Uz"
            d={polylines.Uz}
            stroke={_COLORS.Uz}
            strokeWidth="1.5"
            fill="none"
          />
        )}
        {polylines.p && (
          <path
            data-testid="live-residual-p"
            d={polylines.p}
            stroke={_COLORS.p}
            strokeWidth="2"
            fill="none"
          />
        )}

        {/* Singleton markers — one iterative residual then all
         *  diagonal: shows up here so the chart isn't empty.
         *  Codex 45960a1 round-10 P2-a closure 2026-04-30. */}
        {(["Ux", "Uy", "Uz", "p"] as const).map((key) => {
          const s = singletons[key];
          if (!s) return null;
          return (
            <circle
              key={`singleton-${key}`}
              data-testid={`live-residual-${key}-singleton`}
              cx={s.px}
              cy={s.py}
              r="2.5"
              fill={_COLORS[key]}
            />
          );
        })}

        {/* Legend */}
        {(["Ux", "Uy", "Uz", "p"] as const).map((key, i) => (
          <g key={`legend-${key}`}>
            <line
              x1={_PAD_L + plotW + 14}
              y1={_PAD_T + 12 + i * 18}
              x2={_PAD_L + plotW + 30}
              y2={_PAD_T + 12 + i * 18}
              stroke={_COLORS[key]}
              strokeWidth="2"
            />
            <text
              x={_PAD_L + plotW + 36}
              y={_PAD_T + 16 + i * 18}
              fontSize="11"
              fill="rgb(220,225,235)"
            >
              {key}
            </text>
          </g>
        ))}

        {/* Streaming marker — vertical line at the latest t */}
        {phase === "streaming" && lastRow && (
          <line
            x1={_PAD_L + (lastRow.t / xMax) * plotW}
            y1={_PAD_T}
            x2={_PAD_L + (lastRow.t / xMax) * plotW}
            y2={_PAD_T + plotH}
            stroke="rgba(245,224,100,0.5)"
            strokeWidth="1"
            strokeDasharray="3,3"
          />
        )}
      </svg>

      {/* Status strip */}
      <div className="mt-2 flex items-center justify-between text-[10px] text-surface-500">
        <span>
          {series.length} timestep{series.length === 1 ? "" : "s"} captured
        </span>
        {summary && (
          <span data-testid="live-residual-summary">
            final p init: {summary.last_initial_residual_p?.toExponential(2) ?? "—"} ·
            wall: {summary.wall_time_s.toFixed(1)}s
          </span>
        )}
      </div>

      {errorMessage && (
        <div
          data-testid="live-residual-error"
          className="mt-2 rounded-sm border border-rose-700/50 bg-rose-900/10 px-2 py-1 text-[10px] text-rose-200"
        >
          {errorMessage}
        </div>
      )}
    </div>
  );
}
