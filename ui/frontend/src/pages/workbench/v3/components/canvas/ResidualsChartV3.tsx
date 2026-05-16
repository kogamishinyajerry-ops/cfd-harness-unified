/**
 * V71-UI-V3 · ResidualsChartV3 · log-scale multi-line residual chart
 * Per Image 05 · 5 lines (Ux Uy Uz p continuity) · p in sand-coral as
 * watched curve · target convergence dashed at 10^-5 · current iter
 * dotted vertical.
 *
 * V71 scope: static SVG mock with hand-tuned data points · NOT a live
 * streaming chart. V72+ wires real /api/runs/:id/residuals SSE.
 */
type ResidualKey = "Ux" | "Uy" | "Uz" | "p" | "continuity";

interface ResidualsChartV3Props {
  caseId: string;
  /** V71.J · engineer setting · which residual gets sand-coral highlight. */
  watchedCurve?: ResidualKey;
  /** V71.L · current iteration · drives vertical dotted line. */
  currentIter?: number;
}

// Hand-tuned points: log10(residual) for iter 0..200
function makeLine(start: number, decay: number, oscillate: number = 0): Array<[number, number]> {
  const pts: Array<[number, number]> = [];
  for (let i = 0; i <= 200; i += 5) {
    const noise = oscillate * Math.sin(i / 8) * Math.exp(-i / 60);
    const v = start - decay * i + noise;
    pts.push([i, v]);
  }
  return pts;
}

const LINES: Array<{ key: ResidualKey; pts: Array<[number, number]> }> = [
  { key: "Ux", pts: makeLine(-0.5, 0.028) },
  { key: "Uy", pts: makeLine(-0.7, 0.027) },
  { key: "Uz", pts: makeLine(-1.0, 0.026) },
  { key: "p", pts: makeLine(0.3, 0.024, 0.3) },
  { key: "continuity", pts: makeLine(-1.5, 0.020) },
];

const ACCENT = "#b78b65";
const NEUTRAL = "#82828a";

export function ResidualsChartV3({
  caseId,
  watchedCurve = "p",
  currentIter = 132,
}: ResidualsChartV3Props) {
  // SVG coordinate system: iter -> x in [60, 720] · log residual y in [40, 360]
  // map: iter 0 -> x 60 · iter 200 -> x 720
  // map: log10 = 0 -> y 40 · log10 = -6 -> y 360
  const xMap = (iter: number) => 60 + (iter / 200) * 660;
  const yMap = (logVal: number) => 40 + (-logVal / 6) * 320;

  return (
    <div data-testid="canvas-residuals" className="h-full w-full flex flex-col">
      <div className="text-[11px] uppercase tracking-[0.08em] text-v3-textTertiary px-6 pt-4">
        {caseId} · residual convergence
      </div>
      <svg viewBox="0 0 800 400" className="flex-1 w-full">
        {/* Y-axis gridlines (log decade) */}
        {[0, -1, -2, -3, -4, -5, -6].map((dec) => (
          <g key={dec}>
            <line
              x1="60"
              y1={yMap(dec)}
              x2="720"
              y2={yMap(dec)}
              stroke="#232328"
              strokeWidth="0.5"
            />
            <text
              x="50"
              y={yMap(dec) + 4}
              fill="#82828a"
              fontSize="9"
              fontFamily="JetBrains Mono"
              textAnchor="end"
            >
              10{dec === 0 ? "⁰" : `⁻${Math.abs(dec)}`}
            </text>
          </g>
        ))}
        {/* X-axis ticks */}
        {[0, 50, 100, 150, 200].map((i) => (
          <g key={i}>
            <line
              x1={xMap(i)}
              y1="360"
              x2={xMap(i)}
              y2="365"
              stroke="#82828a"
              strokeWidth="0.5"
            />
            <text
              x={xMap(i)}
              y="378"
              fill="#82828a"
              fontSize="9"
              fontFamily="JetBrains Mono"
              textAnchor="middle"
            >
              {i}
            </text>
          </g>
        ))}
        {/* Axis labels */}
        <text x="40" y="20" fill="#82828a" fontSize="10" fontFamily="Inter">
          residual (log10)
        </text>
        <text
          x="720"
          y="395"
          fill="#82828a"
          fontSize="10"
          fontFamily="Inter"
          textAnchor="end"
        >
          iteration
        </text>
        {/* Target convergence dashed line at 10^-5 */}
        <line
          x1="60"
          y1={yMap(-5)}
          x2="720"
          y2={yMap(-5)}
          stroke="#4a4a52"
          strokeWidth="0.8"
          strokeDasharray="4,3"
        />
        <text
          x="720"
          y={yMap(-5) - 4}
          fill="#4a4a52"
          fontSize="9"
          fontFamily="Inter"
          textAnchor="end"
        >
          target convergence
        </text>
        {/* Current iter vertical dotted line */}
        <line
          x1={xMap(currentIter)}
          y1="40"
          x2={xMap(currentIter)}
          y2="360"
          stroke="#4a4a52"
          strokeWidth="0.5"
          strokeDasharray="2,2"
        />
        <text
          x={xMap(currentIter) + 4}
          y="50"
          fill="#82828a"
          fontSize="9"
          fontFamily="Inter"
        >
          current
        </text>
        {/* 5 residual lines · watched curve in sand-coral · others neutral */}
        {LINES.map((line) => {
          const isWatched = line.key === watchedCurve;
          return (
            <polyline
              key={line.key}
              data-testid={`residual-line-${line.key}`}
              data-watched={isWatched ? "true" : "false"}
              fill="none"
              stroke={isWatched ? ACCENT : NEUTRAL}
              strokeWidth={isWatched ? "1.8" : "1.3"}
              strokeOpacity={isWatched ? 1 : 0.6}
              points={line.pts.map(([x, y]) => `${xMap(x)},${yMap(y)}`).join(" ")}
            />
          );
        })}
        {/* Legend top-right */}
        <g transform="translate(630, 60)" data-testid="residual-legend">
          {LINES.map((line, idx) => {
            const isWatched = line.key === watchedCurve;
            return (
              <g key={line.key} transform={`translate(0, ${idx * 14})`}>
                <rect
                  width="8"
                  height="8"
                  fill={isWatched ? ACCENT : NEUTRAL}
                  opacity={isWatched ? 1 : 0.6}
                />
                <text
                  x="14"
                  y="8"
                  fill={isWatched ? ACCENT : NEUTRAL}
                  fontSize="10"
                  fontFamily="JetBrains Mono"
                  data-testid={`residual-legend-${line.key}`}
                  data-watched={isWatched ? "true" : "false"}
                >
                  {line.key}
                  {isWatched ? " ●" : ""}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}
