import type { AttestVerdict } from "@/types/validation";

// DEC-V61-040: solver-iteration attestor verdict as a distinct chip,
// rendered alongside PassFailChip (scalar contract). The two verdicts
// answer different questions:
//   - PassFailChip: did the scalar measurement land in the gold band?
//   - AttestorBadge: did the solver actually converge cleanly?
// A case can have contract=FAIL + attestor=ATTEST_PASS (LDC audit_real_run:
// clean convergence but wrong profile point picked for scalar) or vice
// versa (cooked scalar on a diverging run). Showing both honestly is the
// point of this DEC.

const STYLES: Record<
  AttestVerdict,
  { bg: string; text: string; dot: string; label: string }
> = {
  ATTEST_PASS: {
    bg: "bg-contract-pass/15",
    text: "text-contract-pass",
    dot: "bg-contract-pass",
    label: "ATTEST PASS",
  },
  ATTEST_HAZARD: {
    bg: "bg-contract-hazard/15",
    text: "text-contract-hazard",
    dot: "bg-contract-hazard",
    label: "ATTEST HAZARD",
  },
  ATTEST_FAIL: {
    bg: "bg-contract-fail/15",
    text: "text-contract-fail",
    dot: "bg-contract-fail",
    label: "ATTEST FAIL",
  },
  ATTEST_NOT_APPLICABLE: {
    bg: "bg-contract-unknown/15",
    text: "text-contract-unknown",
    dot: "bg-contract-unknown",
    label: "NO SOLVER LOG",
  },
};

interface Props {
  overall: AttestVerdict;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function AttestorBadge({ overall, size = "md", className = "" }: Props) {
  const style = STYLES[overall];
  const padding =
    size === "sm"
      ? "px-2 py-0.5 text-xs"
      : size === "lg"
        ? "px-4 py-1.5 text-sm"
        : "px-3 py-1 text-xs";
  const dotSize = size === "lg" ? "h-2 w-2" : "h-1.5 w-1.5";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold uppercase tracking-wider ${padding} ${style.bg} ${style.text} ${className}`}
      role="status"
      aria-label={`attestor verdict ${style.label.toLowerCase()}`}
      title="Solver-iteration attestor (A1–A6): did the solver actually converge?"
    >
      <span className={`inline-block rounded-full ${dotSize} ${style.dot}`} />
      {style.label}
    </span>
  );
}
