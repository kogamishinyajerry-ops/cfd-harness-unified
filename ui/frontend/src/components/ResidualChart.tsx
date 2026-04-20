import { useMemo } from "react";

// Inline SVG log-scale chart for residual streams. Keeps frontend
// bundle light — Phase 3 deliberately avoids chart.js / recharts /
// plotly to preserve the 70 KB gzipped JS budget from Phase 0.

export interface ResidualSample {
  iter: number;
  Ux: number;
  Uy: number;
  p: number;
}

interface Props {
  samples: ResidualSample[];
  height?: number;
  width?: number;
}

const CHANNELS = [
  { key: "Ux" as const, color: "#60a5fa" /* blue */ },
  { key: "Uy" as const, color: "#f472b6" /* pink */ },
  { key: "p"  as const, color: "#facc15" /* yellow */ },
];

const LOG10_MIN = -12;
const LOG10_MAX = 0.5;

function toY(value: number, top: number, bottom: number): number {
  const log = Math.log10(Math.max(value, 1e-20));
  const clamped = Math.max(Math.min(log, LOG10_MAX), LOG10_MIN);
  const ratio = (LOG10_MAX - clamped) / (LOG10_MAX - LOG10_MIN);
  return top + ratio * (bottom - top);
}

export function ResidualChart({ samples, height = 280, width = 720 }: Props) {
  const padL = 56, padR = 16, padT = 16, padB = 26;
  const plotL = padL, plotR = width - padR;
  const plotT = padT, plotB = height - padB;

  const maxIter = Math.max(1, samples[samples.length - 1]?.iter ?? 1);
  const xStep = (plotR - plotL) / Math.max(maxIter, 1);

  const paths = useMemo(() => {
    return CHANNELS.map((ch) => {
      if (samples.length === 0) return { key: ch.key, color: ch.color, d: "" };
      const d = samples
        .map((s, i) => {
          const x = plotL + s.iter * xStep;
          const y = toY(s[ch.key], plotT, plotB);
          return `${i === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`;
        })
        .join(" ");
      return { key: ch.key, color: ch.color, d };
    });
  }, [samples, plotL, plotT, plotB, xStep]);

  const gridLogs = [0, -2, -4, -6, -8, -10];
  const last = samples[samples.length - 1];

  return (
    <div className="rounded-md border border-surface-800 bg-surface-950/60 p-3">
      <div className="flex items-baseline justify-between pb-2">
        <h3 className="text-[11px] uppercase tracking-wider text-surface-400">Residual history</h3>
        <div className="flex items-center gap-3 text-[10px]">
          {CHANNELS.map((c) => (
            <span key={c.key} className="inline-flex items-center gap-1 text-surface-400">
              <span aria-hidden style={{ backgroundColor: c.color }} className="inline-block h-1.5 w-3 rounded-sm" />
              {c.key}
              {last && <code className="font-mono text-surface-300">{last[c.key].toExponential(2)}</code>}
            </span>
          ))}
        </div>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto">
        {/* y-axis grid + labels */}
        {gridLogs.map((log) => {
          const y = toY(10 ** log, plotT, plotB);
          return (
            <g key={log}>
              <line x1={plotL} x2={plotR} y1={y} y2={y} stroke="#1f2937" strokeDasharray="2 3" />
              <text x={plotL - 6} y={y + 3} textAnchor="end" fontSize="10" fill="#64748b">
                1e{log}
              </text>
            </g>
          );
        })}
        {/* axes */}
        <line x1={plotL} x2={plotR} y1={plotB} y2={plotB} stroke="#475569" />
        <line x1={plotL} x2={plotL} y1={plotT} y2={plotB} stroke="#475569" />
        {/* x-label */}
        <text x={plotL} y={plotB + 16} fontSize="10" fill="#64748b">iter 0</text>
        <text x={plotR} y={plotB + 16} textAnchor="end" fontSize="10" fill="#64748b">iter {maxIter}</text>
        {/* paths */}
        {paths.map((p) => (
          <path key={p.key} d={p.d} fill="none" stroke={p.color} strokeWidth="1.5" />
        ))}
      </svg>
    </div>
  );
}
