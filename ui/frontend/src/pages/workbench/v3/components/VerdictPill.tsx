// V73.4 · Shared VerdictPill primitive.
//
// Until V73, there were two verdict-pill implementations and a third inlined
// in MultiCaseRibbonV3 — all mapping a verdict string to (color, label). This
// drifted: the ribbon and TruthChainContent used different palettes for the
// same `PENDING` state. V73.4 collapses them into one primitive + one
// normalizer, owned by the v3 shell.
//
// Read-only · no buttons · no mutating affordance. V130/V132 contract holds.

export type VerdictKind =
  | "PASS"
  | "PASS_WITH_DISCLAIMER"
  | "FAIL"
  | "PENDING"
  | "INCONCLUSIVE";

/**
 * Normalize raw verdict strings from various backends/sources into VerdictKind.
 *
 * Accepts:
 *   - TrustGate verdicts: PASS / PASS_WITH_DISCLAIMER / FAIL / PENDING / INCONCLUSIVE
 *   - contract_status values: audit-passing / audit-failing / gold-pending
 *   - Lowercase variants of any of the above
 *
 * Unknown values map to INCONCLUSIVE (calm, not red).
 */
export function normalizeVerdict(raw?: string | null): VerdictKind {
  if (!raw) return "PENDING";
  const up = String(raw).toUpperCase().replace(/-/g, "_");
  switch (up) {
    case "PASS":
    case "AUDIT_PASSING":
      return "PASS";
    case "FAIL":
    case "AUDIT_FAILING":
      return "FAIL";
    case "PASS_WITH_DISCLAIMER":
      return "PASS_WITH_DISCLAIMER";
    case "PENDING":
    case "GOLD_PENDING":
      return "PENDING";
    default:
      return "INCONCLUSIVE";
  }
}

interface VerdictPillProps {
  verdict: VerdictKind | string | null | undefined;
  /** Override the displayed label (defaults to the normalized verdict). */
  label?: string;
  /** Override the data-testid (defaults to "verdict-pill"). */
  "data-testid"?: string;
  /** Compact 2-letter pill (PASS → "P") vs the full-text variant. */
  compact?: boolean;
}

const TONE: Record<
  VerdictKind,
  { fg: string; border: string; dot: string; label: string; short: string }
> = {
  PASS: {
    fg: "text-v3-inlet",
    border: "border-v3-inlet/40",
    dot: "bg-v3-inlet",
    label: "PASS",
    short: "P",
  },
  PASS_WITH_DISCLAIMER: {
    fg: "text-v3-symmetry",
    border: "border-v3-symmetry/40",
    dot: "bg-v3-symmetry",
    label: "PASS w/ DISCLAIMER",
    short: "P!",
  },
  FAIL: {
    fg: "text-v3-wall",
    border: "border-v3-wall/40",
    dot: "bg-v3-wall",
    label: "FAIL",
    short: "F",
  },
  PENDING: {
    fg: "text-v3-textTertiary",
    border: "border-v3-border",
    dot: "bg-v3-border",
    label: "PENDING",
    short: "—",
  },
  INCONCLUSIVE: {
    fg: "text-v3-textTertiary",
    border: "border-v3-border",
    dot: "bg-v3-border",
    label: "INCONCLUSIVE",
    short: "?",
  },
};

export function VerdictPill({
  verdict,
  label,
  compact,
  "data-testid": testId = "verdict-pill",
}: VerdictPillProps) {
  const kind = normalizeVerdict(typeof verdict === "string" ? verdict : verdict ?? null);
  const tone = TONE[kind];
  return (
    <span
      data-testid={testId}
      data-verdict={kind}
      className={`inline-flex items-center gap-1 text-[11px] uppercase tracking-[0.08em] px-2 py-0.5 border rounded ${tone.fg} ${tone.border}`}
    >
      <span
        aria-hidden
        className={`inline-block w-1.5 h-1.5 rounded-full ${tone.dot}`}
      />
      {compact ? tone.short : label ?? tone.label.toLowerCase()}
    </span>
  );
}

/** Color/dot mapping for surfaces that want their own pill chrome but the
 * canonical V73.4 tone. (Used by MultiCaseRibbon's compact chip header.) */
export function verdictTone(raw?: string | null) {
  return TONE[normalizeVerdict(raw)];
}
