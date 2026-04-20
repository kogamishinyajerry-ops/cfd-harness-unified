import type { ContractStatus } from "@/types/validation";

// Single-axis band chart rendered as inline SVG — no Plotly needed for
// Phase 0. Shows:
//   - tolerance band [lower, upper] as a shaded horizontal rectangle
//   - gold reference value as a vertical tick
//   - measured value as a colored tick (color tracks contract status)
//
// Keeping this as hand-rolled SVG (≤100 LOC) buys us:
//   - zero extra JS bundle weight at Phase 0
//   - no FOUC when Plotly loads
//   - trivial a11y: raw numbers are printed below the axis already.

interface Props {
  refValue: number;
  lower: number;
  upper: number;
  measurement: number | null;
  unit: string;
  status: ContractStatus;
}

const STATUS_COLOR: Record<ContractStatus, string> = {
  PASS: "#4ade80",
  HAZARD: "#fbbf24",
  FAIL: "#f87171",
  UNKNOWN: "#7f8fa4",
};

export function BandChart({
  refValue,
  lower,
  upper,
  measurement,
  unit,
  status,
}: Props) {
  // Domain that always encompasses ref ± tolerance + measurement.
  const candidates = [lower, upper, refValue];
  if (measurement !== null) candidates.push(measurement);
  const rawMin = Math.min(...candidates);
  const rawMax = Math.max(...candidates);
  const span = Math.max(rawMax - rawMin, Math.abs(refValue) * 0.05 || 1e-6);
  const pad = span * 0.12;
  const xMin = rawMin - pad;
  const xMax = rawMax + pad;

  const width = 640;
  const height = 120;
  const leftPad = 24;
  const rightPad = 24;
  const usable = width - leftPad - rightPad;

  const toX = (v: number) =>
    leftPad + ((v - xMin) / (xMax - xMin)) * usable;

  const bandY = 44;
  const bandH = 32;

  const measurementColor = STATUS_COLOR[status];

  const format = (v: number): string => {
    if (Math.abs(v) >= 100 || Math.abs(v) < 1e-3) return v.toExponential(3);
    return v.toFixed(4);
  };

  return (
    <figure className="font-mono">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full"
        role="img"
        aria-label={`tolerance band chart: reference ${format(refValue)}${unit ? " " + unit : ""}, band [${format(lower)}, ${format(upper)}], measurement ${measurement === null ? "none" : format(measurement)}`}
      >
        {/* Axis baseline */}
        <line
          x1={leftPad}
          x2={width - rightPad}
          y1={bandY + bandH + 18}
          y2={bandY + bandH + 18}
          stroke="#3a495f"
          strokeWidth={1}
        />
        {/* Tolerance band */}
        <rect
          x={toX(lower)}
          y={bandY}
          width={toX(upper) - toX(lower)}
          height={bandH}
          fill="#4ade80"
          fillOpacity={0.12}
          stroke="#4ade80"
          strokeOpacity={0.4}
          strokeWidth={1}
        />
        {/* Ref tick */}
        <line
          x1={toX(refValue)}
          x2={toX(refValue)}
          y1={bandY - 6}
          y2={bandY + bandH + 6}
          stroke="#d5dbe2"
          strokeWidth={1.5}
          strokeDasharray="3 2"
        />
        <text
          x={toX(refValue)}
          y={bandY - 10}
          textAnchor="middle"
          fontSize={10}
          fill="#d5dbe2"
        >
          ref {format(refValue)}
        </text>
        {/* Measurement tick */}
        {measurement !== null && (
          <>
            <line
              x1={toX(measurement)}
              x2={toX(measurement)}
              y1={bandY - 10}
              y2={bandY + bandH + 10}
              stroke={measurementColor}
              strokeWidth={2.5}
            />
            <circle
              cx={toX(measurement)}
              cy={bandY + bandH / 2}
              r={4.5}
              fill={measurementColor}
            />
            <text
              x={toX(measurement)}
              y={bandY + bandH + 34}
              textAnchor="middle"
              fontSize={10}
              fill={measurementColor}
            >
              meas {format(measurement)}
            </text>
          </>
        )}
        {/* Axis ends */}
        <text
          x={leftPad}
          y={bandY + bandH + 34}
          fontSize={9}
          fill="#7f8fa4"
        >
          {format(xMin)}
        </text>
        <text
          x={width - rightPad}
          y={bandY + bandH + 34}
          fontSize={9}
          textAnchor="end"
          fill="#7f8fa4"
        >
          {format(xMax)}
        </text>
      </svg>
      <figcaption className="mt-1 text-[11px] text-surface-400">
        Green band: gold-reference ± tolerance. Dashed tick: reference value.
        Colored tick: measured value (color = contract state).
      </figcaption>
    </figure>
  );
}
