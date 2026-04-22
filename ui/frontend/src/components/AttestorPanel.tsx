import type { AttestorVerdict } from "@/types/validation";
import { AttestorBadge } from "./AttestorBadge";

// DEC-V61-040: per-check breakdown of the A1..A6 solver-iteration attestor.
// Renders each check with its verdict + concern_type + summary so the user
// can see *why* the attestor reached its overall verdict. Colocates with
// AuditConcernList on the lower grid of ValidationReportPage.

const CHECK_DESCRIPTIONS: Record<string, string> = {
  A1: "Solver crash log",
  A2: "Residual progress",
  A3: "Final residuals vs floor",
  A4: "Pressure-loop iteration cap",
  A5: "Time-step block count",
  A6: "Bounding/recurrent turbulence markers",
};

const VERDICT_STYLE: Record<string, string> = {
  PASS: "text-contract-pass",
  HAZARD: "text-contract-hazard",
  FAIL: "text-contract-fail",
};

interface Props {
  attestation: AttestorVerdict | null;
}

export function AttestorPanel({ attestation }: Props) {
  // Treat "no fixture block" and "explicit ATTEST_NOT_APPLICABLE with no
  // checks" as the same rendering case — both mean "no solver evidence".
  // Per Codex DEC-040 round-1 FLAG, explicit NOT_APPLICABLE shouldn't render
  // an empty panel body after the badge header.
  const noSolverEvidence =
    !attestation ||
    attestation.overall === "ATTEST_NOT_APPLICABLE" ||
    attestation.checks.length === 0;
  if (noSolverEvidence) {
    return (
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <h3 className="card-title">Convergence Attestor (A1–A6)</h3>
          {attestation && (
            <AttestorBadge overall={attestation.overall} size="sm" />
          )}
        </div>
        <p className="px-4 py-4 text-xs text-surface-400">
          No solver log available for this run (reference / visual-only).
          The attestor only runs against real OpenFOAM output.
        </p>
      </div>
    );
  }
  return (
    <div className="card">
      <div className="card-header flex items-center justify-between">
        <h3 className="card-title">Convergence Attestor (A1–A6)</h3>
        <AttestorBadge overall={attestation.overall} size="sm" />
      </div>
      <ul className="divide-y divide-surface-800/60">
        {attestation.checks.map((check) => (
          <li key={check.check_id} className="flex items-start gap-3 px-4 py-3">
            <span className="mono text-[11px] font-semibold text-surface-400 w-8 shrink-0">
              {check.check_id}
            </span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-surface-200">
                  {CHECK_DESCRIPTIONS[check.check_id] ?? check.check_id}
                </span>
                <span
                  className={`mono text-[10px] font-semibold uppercase tracking-wider ${VERDICT_STYLE[check.verdict] ?? "text-surface-300"}`}
                >
                  {check.verdict}
                </span>
              </div>
              {check.summary && (
                <p className="mt-1 text-[11px] leading-snug text-surface-400">
                  {check.summary}
                </p>
              )}
              {check.concern_type && (
                <p className="mono mt-0.5 text-[10px] text-surface-500">
                  {check.concern_type}
                </p>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
