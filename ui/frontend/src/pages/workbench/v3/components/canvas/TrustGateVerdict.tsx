/**
 * V71-UI-V3 · V71.Q · TrustGateVerdict component
 *
 * Per .planning/blueprints/v3/INDEX.md Image 07.
 *
 * Renders a large verdict block: PASS / PASS_WITH_DISCLAIMER / FAIL /
 * INCONCLUSIVE · semantic color dot · summary line · provenance section ·
 * point-by-point comparison table.
 *
 * Display-only · the verdict is computed server-side from `/api/cases/:id/
 * completeness` and rendered here. There is NO "promote to gold" or
 * "override verdict" affordance in the v3 surface (V130 invariant).
 *
 * V71.R (GoldPromotionPath) lives in a separate sub-DEC and routes from
 * here as a quiet text link only.
 */

export type TrustGateState =
  | "PASS"
  | "PASS_WITH_DISCLAIMER"
  | "FAIL"
  | "PENDING"
  | "INCONCLUSIVE";

interface PointComparison {
  y_norm: number;
  gold: number;
  computed: number;
  error_pct: number;
}

interface TrustGateVerdictProps {
  caseId: string;
  verdict: TrustGateState;
  /** Brief one-line summary (e.g., "12/17 points within ±5%"). */
  summary: string;
  /** Up to 6 point-by-point comparisons surfaced inline. */
  points?: PointComparison[];
  /** Provenance metadata. */
  corpusSha?: string;
  solverVersion?: string;
  goldStandard?: string;
}

const VERDICT_TONE: Record<TrustGateState, { fg: string; bg: string; label: string }> = {
  PASS: {
    fg: "text-v3-inlet",
    bg: "border-v3-inlet/40 bg-v3-inlet/5",
    label: "PASS",
  },
  PASS_WITH_DISCLAIMER: {
    fg: "text-v3-symmetry",
    bg: "border-v3-symmetry/40 bg-v3-symmetry/5",
    label: "PASS w/ DISCLAIMER",
  },
  FAIL: {
    fg: "text-v3-wall",
    bg: "border-v3-wall/40 bg-v3-wall/5",
    label: "FAIL",
  },
  PENDING: {
    fg: "text-v3-textTertiary",
    bg: "border-v3-border",
    label: "PENDING",
  },
  INCONCLUSIVE: {
    fg: "text-v3-textTertiary",
    bg: "border-v3-border",
    label: "INCONCLUSIVE",
  },
};

export function TrustGateVerdict({
  caseId,
  verdict,
  summary,
  points,
  corpusSha,
  solverVersion,
  goldStandard,
}: TrustGateVerdictProps) {
  const tone = VERDICT_TONE[verdict];
  return (
    <div
      data-testid="trustgate-verdict-block"
      data-verdict={verdict}
      className={`px-6 py-5 border rounded-md ${tone.bg}`}
    >
      <div className="flex items-baseline justify-between mb-2">
        <div className={`text-[34px] font-light tracking-tight ${tone.fg}`}>
          {tone.label}
        </div>
        <div className="text-[11px] uppercase tracking-[0.08em] text-v3-textTertiary font-mono">
          {caseId}
        </div>
      </div>
      <p
        data-testid="trustgate-summary"
        className="text-[13px] text-v3-textSecondary leading-relaxed mb-4"
      >
        {summary}
      </p>

      {points && points.length > 0 && (
        <div
          data-testid="trustgate-points-table"
          className="border-t border-v3-border pt-3 mb-3"
        >
          <div className="text-[10px] uppercase tracking-[0.08em] text-v3-textTertiary mb-2">
            point-by-point comparison · y/H · gold · computed · err%
          </div>
          <div className="text-[12px] font-mono space-y-0.5">
            {points.map((p, i) => {
              const ok = Math.abs(p.error_pct) <= 5;
              return (
                <div
                  key={i}
                  data-testid={`trustgate-point-${i}`}
                  className="flex justify-between text-v3-textSecondary tabular-nums"
                >
                  <span className="w-16">{p.y_norm.toFixed(4)}</span>
                  <span className="w-20 text-right">{p.gold.toFixed(4)}</span>
                  <span className="w-20 text-right">{p.computed.toFixed(4)}</span>
                  <span
                    className={`w-16 text-right ${
                      ok ? "text-v3-inlet" : "text-v3-wall"
                    }`}
                  >
                    {p.error_pct >= 0 ? "+" : ""}
                    {p.error_pct.toFixed(2)}%
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div
        data-testid="trustgate-provenance"
        className="border-t border-v3-border pt-3 text-[11px] text-v3-textTertiary font-mono space-y-0.5"
      >
        {goldStandard && (
          <div>gold: {goldStandard}</div>
        )}
        {solverVersion && <div>solver: {solverVersion}</div>}
        {corpusSha && <div>corpus: {corpusSha.slice(0, 12)}</div>}
      </div>
    </div>
  );
}
