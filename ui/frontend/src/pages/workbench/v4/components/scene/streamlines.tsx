/**
 * V4 · Streamline overlay generator · per UI-SPEC §3.3
 *
 * Generates ≥60 curved Bezier paths that wrap around the engine assembly,
 * color graded cool→hot from inlet (left) to outlet (right). Deterministic
 * given the same seed so layout stays stable across re-renders.
 *
 * Designed to be slotted into IndustrialBoxScene's `children` prop.
 *
 * Coordinate space: matches IndustrialBoxScene viewBox 640×360. Engine
 * spans roughly x=210..490 · y=110..195.
 */
import { V4_CFD_COLORMAP, V4_PALETTE } from "@/theme/industrial_minimalist";

// Deterministic LCG so streamlines stay byte-stable across renders.
function lcg(seed: number) {
  let state = seed;
  return () => {
    state = (state * 9301 + 49297) % 233280;
    return state / 233280;
  };
}

// Cool→hot palette · references V4_CFD_COLORMAP (the canonical CFD
// colormap token) so streamlines + body contour + colorbar all agree.
const STREAM_PALETTE = V4_CFD_COLORMAP;

function colorAt(t: number): string {
  const idx = Math.min(STREAM_PALETTE.length - 1, Math.max(0, Math.floor(t * STREAM_PALETTE.length)));
  return STREAM_PALETTE[idx];
}

export interface StreamlineFieldProps {
  /** Number of streamlines · UI-SPEC requires ≥60 for solver. */
  count?: number;
  /** Deterministic seed. */
  seed?: number;
  /** Global opacity multiplier (for DOE thumbnails this is lower). */
  opacityMul?: number;
  /** Stroke width baseline (DOE thumbnails use 0.4, full scene 0.7). */
  baseStroke?: number;
  /** When true, paths animate via stroke-dashoffset. */
  animated?: boolean;
}

/**
 * Render N curved streamlines wrapping from inlet around engine body
 * to outlet. Each path is a cubic Bezier with randomized control points
 * within a band above / below the engine centerline.
 */
export function StreamlineField({
  count = 72,
  seed = 17,
  opacityMul = 1,
  baseStroke = 0.7,
  animated = false,
}: StreamlineFieldProps) {
  const rand = lcg(seed);

  const paths: {
    d: string;
    color: string;
    width: number;
    opacity: number;
    dashLength: number;
  }[] = [];

  for (let i = 0; i < count; i++) {
    const tNorm = i / Math.max(1, count - 1); // 0..1
    // Vertical band · upper half (yBand 70..148) or lower half (152..230).
    const isUpper = rand() < 0.5;
    const yStart = isUpper
      ? 88 + rand() * 60 // 88..148
      : 155 + rand() * 70; // 155..225

    // X start: just left of inlet · slight scatter
    const x0 = 80 + rand() * 80; // 80..160
    // Control points wrap up-over (upper band) or down-under (lower band)
    const peakY = isUpper ? yStart - (28 + rand() * 18) : yStart + (28 + rand() * 18);
    const c1x = 220 + rand() * 40;
    const c1y = peakY;
    const c2x = 380 + rand() * 50;
    const c2y = isUpper ? peakY + 10 + rand() * 18 : peakY - 10 - rand() * 18;
    // X end: past nozzle with slight scatter
    const x1 = 530 + rand() * 80; // 530..610
    const y1 = yStart + (rand() - 0.5) * 12; // small wander

    const d = `M ${x0.toFixed(1)},${yStart.toFixed(1)} C ${c1x.toFixed(1)},${c1y.toFixed(1)} ${c2x.toFixed(1)},${c2y.toFixed(1)} ${x1.toFixed(1)},${y1.toFixed(1)}`;

    const color = colorAt(tNorm);
    const width = baseStroke + rand() * 0.6;
    const opacity = (0.55 + rand() * 0.35) * opacityMul;
    // Visual dash length (path length approximation).
    const dashLength = 320 + rand() * 120;

    paths.push({ d, color, width, opacity, dashLength });
  }

  return (
    <g data-testid="v4-streamline-field" pointerEvents="none">
      {paths.map((p, i) => (
        <path
          key={i}
          d={p.d}
          fill="none"
          stroke={p.color}
          strokeWidth={p.width}
          strokeLinecap="round"
          opacity={p.opacity}
          strokeDasharray={animated ? `${p.dashLength * 0.35} ${p.dashLength}` : undefined}
          style={
            animated
              ? {
                  animation: `v4-stream ${4 + (i % 7) * 0.5}s linear infinite`,
                }
              : undefined
          }
        />
      ))}
      {/* Velocity arrowheads on a subset of streamlines · sparse */}
      {paths
        .filter((_, i) => i % 9 === 0)
        .map((p, i) => {
          // Place an arrowhead near the path end (approximated · matches x1)
          const m = p.d.match(/([\d.]+),([\d.]+)$/);
          if (!m) return null;
          const x = parseFloat(m[1]);
          const y = parseFloat(m[2]);
          return (
            <polygon
              key={`a-${i}`}
              points={`${x},${y} ${x - 5},${y - 2.4} ${x - 5},${y + 2.4}`}
              fill={p.color}
              opacity={p.opacity * 0.85}
            />
          );
        })}

      <style>{`@keyframes v4-stream { from { stroke-dashoffset: 0; } to { stroke-dashoffset: -440; } }`}</style>
    </g>
  );
}

/**
 * Render a horizontal velocity colorbar legend · bottom-right of scene.
 * Used in post / solver modes.
 */
export function VelocityColorbar({
  x = 480,
  y = 240,
  width = 130,
  height = 8,
  label = "速度 m/s",
  min = "0.0",
  max = "42.6",
}: {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  label?: string;
  min?: string;
  max?: string;
}) {
  return (
    <g data-testid="v4-velocity-colorbar">
      <defs>
        <linearGradient id="v4-velocity-grad" x1="0" x2="1" y1="0" y2="0">
          {STREAM_PALETTE.map((c, i) => (
            <stop key={i} offset={`${(i / (STREAM_PALETTE.length - 1)) * 100}%`} stopColor={c} />
          ))}
        </linearGradient>
      </defs>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill="url(#v4-velocity-grad)"
        stroke={V4_PALETTE.border}
        strokeWidth="0.4"
      />
      <text
        x={x}
        y={y - 4}
        fontSize="8"
        fill={V4_PALETTE.textSecondary}
        fontFamily="ui-monospace, monospace"
      >
        {label}
      </text>
      <text
        x={x}
        y={y + height + 9}
        fontSize="7.5"
        fill={V4_PALETTE.textTertiary}
        fontFamily="ui-monospace, monospace"
      >
        {min}
      </text>
      <text
        x={x + width}
        y={y + height + 9}
        fontSize="7.5"
        fill={V4_PALETTE.textTertiary}
        fontFamily="ui-monospace, monospace"
        textAnchor="end"
      >
        {max}
      </text>
    </g>
  );
}
