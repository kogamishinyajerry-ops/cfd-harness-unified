import type { ContractStatus } from "@/types/validation";

// Three-state chip — never reduced to binary.
// Design principle (docs/ui_design.md #2): HAZARD is the most
// commercially important state because it represents "green on the
// number but unsafe to publish". We give it visual prominence equal
// to FAIL, not a softer "warning" tone.

const STYLES: Record<ContractStatus, { bg: string; text: string; dot: string; label: string }> = {
  PASS: {
    bg: "bg-contract-pass/15",
    text: "text-contract-pass",
    dot: "bg-contract-pass",
    label: "PASS",
  },
  HAZARD: {
    bg: "bg-contract-hazard/15",
    text: "text-contract-hazard",
    dot: "bg-contract-hazard",
    label: "HAZARD",
  },
  FAIL: {
    bg: "bg-contract-fail/15",
    text: "text-contract-fail",
    dot: "bg-contract-fail",
    label: "FAIL",
  },
  UNKNOWN: {
    bg: "bg-contract-unknown/15",
    text: "text-contract-unknown",
    dot: "bg-contract-unknown",
    label: "NO RUN",
  },
};

interface Props {
  status: ContractStatus;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function PassFailChip({ status, size = "md", className = "" }: Props) {
  const style = STYLES[status];
  const padding =
    size === "sm" ? "px-2 py-0.5 text-xs" : size === "lg" ? "px-4 py-1.5 text-sm" : "px-3 py-1 text-xs";
  const dotSize = size === "lg" ? "h-2 w-2" : "h-1.5 w-1.5";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold uppercase tracking-wider ${padding} ${style.bg} ${style.text} ${className}`}
      role="status"
      aria-label={`contract status ${style.label.toLowerCase()}`}
    >
      <span className={`inline-block rounded-full ${dotSize} ${style.dot}`} />
      {style.label}
    </span>
  );
}
