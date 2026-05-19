/**
 * V80.4 · ComparatorV4 · gold-vs-actual SVG comparator (V4.C contract)
 *
 * Per .planning/blueprints/v4/INDEX.md Contract V4.C:
 *   - SVG-based · NO canvas / NO chart library dependency (LLM-offline 4Q gate)
 *   - Two curves overlaid: computed (solid sand-coral 1.8) + Ghia reference
 *     (open circles, stroke #9a9aa0, r=4)
 *   - ±5% tolerance band: sand-coral fill, opacity 0.08
 *   - 17 reference points (Ghia 1982 canonical lid_driven_cavity)
 *   - Worst-point highlight: dusty-amber #a89060 small dot + max-|Δu| annotation
 *   - data-testid: comparator-gold-actual-{case_id}-{quantity}
 *
 * This is a COMPLEMENT to GoldDeltaPanel (which is tabular), and lives in the
 * step-5 viewport view (mounted from ReportComparisonV3).
 *
 * V130/V132 invariants: this is pure SVG render from static reference data;
 * no buttons, no mutation, no LLM call.
 */
import {
  GHIA_LID_CAVITY_U_CENTERLINE,
  computeLidCavityComputed,
  worstDelta,
} from "@/data/gold_references";

interface ComparatorV4Props {
  caseId: string;
  /** Reference quantity; only "u_centerline" is supported in V80.4. */
  quantity?: "u_centerline";
}

const W = 800;
const H = 400;
const PAD_LEFT = 80;
const PAD_RIGHT = 80;
const PAD_TOP = 40;
const PAD_BOTTOM = 60;
const PLOT_W = W - PAD_LEFT - PAD_RIGHT;
const PLOT_H = H - PAD_TOP - PAD_BOTTOM;

const U_MIN = -0.4;
const U_MAX = 1.0;
const Y_MIN = 0;
const Y_MAX = 1;

const SANDCORAL = "#b78b65";
const DUSTYAMBER = "#a89060";
const TEXT_TERTIARY = "#82828a";
const GRIDLINE = "#232328";

const xMap = (u: number) =>
  PAD_LEFT + ((u - U_MIN) / (U_MAX - U_MIN)) * PLOT_W;
const yMap = (yh: number) =>
  PAD_TOP + (1 - (yh - Y_MIN) / (Y_MAX - Y_MIN)) * PLOT_H;

export function ComparatorV4({
  caseId,
  quantity = "u_centerline",
}: ComparatorV4Props) {
  const reference = GHIA_LID_CAVITY_U_CENTERLINE;
  const computed = computeLidCavityComputed();
  const { index: worstIdx, abs_delta_pct: maxAbsPct } = worstDelta(
    reference,
    computed,
  );
  const [worstYh, worstComputedU] = computed[worstIdx];

  return (
    <section
      data-testid={`comparator-gold-actual-${caseId}-${quantity}`}
      data-quantity={quantity}
      data-case-id={caseId}
      aria-label="Gold-vs-actual comparator"
      className="px-6 pt-2 pb-4 border-t border-v3-border"
    >
      <header className="flex items-baseline justify-between mb-2">
        <h3 className="text-[11px] uppercase tracking-[0.08em] text-v3-textTertiary">
          gold-vs-actual · u-centerline · Ghia 1982 reference
        </h3>
        <span
          data-testid="comparator-max-delta"
          className="text-[11px] font-mono text-v3-textSecondary"
        >
          max |Δu| = {maxAbsPct.toFixed(2)}%
        </span>
      </header>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        role="img"
        aria-label="Gold-vs-actual u-centerline comparator"
      >
        {/* Gridlines · y */}
        {[0, 0.25, 0.5, 0.75, 1.0].map((t) => (
          <g key={`gy-${t}`}>
            <line
              x1={PAD_LEFT}
              y1={yMap(t)}
              x2={W - PAD_RIGHT}
              y2={yMap(t)}
              stroke={GRIDLINE}
              strokeWidth="0.4"
            />
            <text
              x={PAD_LEFT - 10}
              y={yMap(t) + 4}
              fill={TEXT_TERTIARY}
              fontSize="9"
              fontFamily="JetBrains Mono"
              textAnchor="end"
            >
              {t.toFixed(2)}
            </text>
          </g>
        ))}
        {/* Gridlines · x */}
        {[-0.4, -0.2, 0, 0.2, 0.4, 0.6, 0.8, 1.0].map((u) => (
          <g key={`gx-${u}`}>
            <line
              x1={xMap(u)}
              y1={PAD_TOP}
              x2={xMap(u)}
              y2={H - PAD_BOTTOM}
              stroke={GRIDLINE}
              strokeWidth="0.4"
            />
            <text
              x={xMap(u)}
              y={H - PAD_BOTTOM + 16}
              fill={TEXT_TERTIARY}
              fontSize="9"
              fontFamily="JetBrains Mono"
              textAnchor="middle"
            >
              {u.toFixed(1)}
            </text>
          </g>
        ))}
        <text
          x={PAD_LEFT - 50}
          y={PAD_TOP - 8}
          fill={TEXT_TERTIARY}
          fontSize="11"
          fontFamily="Inter"
        >
          y/H
        </text>
        <text
          x={W - PAD_RIGHT}
          y={H - PAD_BOTTOM + 36}
          fill={TEXT_TERTIARY}
          fontSize="11"
          fontFamily="Inter"
          textAnchor="end"
        >
          u (normalized)
        </text>
        {/* ±5% tolerance band */}
        <path
          data-testid="comparator-tolerance-band"
          d={`M ${computed
            .map(([yh, u]) => `${xMap(u - 0.05)},${yMap(yh)}`)
            .join(" L ")} L ${computed
            .slice()
            .reverse()
            .map(([yh, u]) => `${xMap(u + 0.05)},${yMap(yh)}`)
            .join(" L ")} Z`}
          fill={SANDCORAL}
          fillOpacity="0.08"
        />
        {/* Computed polyline · sand-coral 1.8 */}
        <polyline
          data-testid="comparator-computed-curve"
          fill="none"
          stroke={SANDCORAL}
          strokeWidth="1.8"
          points={computed
            .map(([yh, u]) => `${xMap(u)},${yMap(yh)}`)
            .join(" ")}
        />
        {/* Ghia reference · 17 open circles */}
        {reference.map(([yh, u], i) => (
          <circle
            key={`ref-${i}`}
            data-testid="comparator-reference-point"
            cx={xMap(u)}
            cy={yMap(yh)}
            r="4"
            fill="none"
            stroke="#9a9aa0"
            strokeWidth="1.4"
          />
        ))}
        {/* Worst-point highlight · dusty-amber */}
        <circle
          data-testid="comparator-worst-point"
          cx={xMap(worstComputedU)}
          cy={yMap(worstYh)}
          r="3.5"
          fill={DUSTYAMBER}
          stroke="none"
        />
        <text
          x={xMap(worstComputedU) + 8}
          y={yMap(worstYh) - 6}
          fill={DUSTYAMBER}
          fontSize="10"
          fontFamily="JetBrains Mono"
        >
          max |Δu| = {maxAbsPct.toFixed(2)}%
        </text>
        {/* Legend */}
        <g transform={`translate(${W - PAD_RIGHT - 160}, ${PAD_TOP + 10})`}>
          <line
            x1="0"
            y1="6"
            x2="22"
            y2="6"
            stroke={SANDCORAL}
            strokeWidth="1.8"
          />
          <text
            x="28"
            y="10"
            fill={TEXT_TERTIARY}
            fontSize="10"
            fontFamily="Inter"
          >
            computed
          </text>
          <circle
            cx="11"
            cy="26"
            r="4"
            fill="none"
            stroke="#9a9aa0"
            strokeWidth="1.4"
          />
          <text
            x="28"
            y="30"
            fill={TEXT_TERTIARY}
            fontSize="10"
            fontFamily="Inter"
          >
            Ghia 1982
          </text>
          <circle cx="11" cy="46" r="3.5" fill={DUSTYAMBER} stroke="none" />
          <text
            x="28"
            y="50"
            fill={TEXT_TERTIARY}
            fontSize="10"
            fontFamily="Inter"
          >
            worst point
          </text>
        </g>
      </svg>
    </section>
  );
}
