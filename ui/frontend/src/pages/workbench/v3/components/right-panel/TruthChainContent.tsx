/**
 * V71-UI-V3 · TruthChainContent · right-panel TruthChain tab
 *
 * Per .planning/blueprints/v3/INDEX.md Image 05/07 (provenance chain).
 *
 * Surfaces the verifiable provenance chain for a case + run:
 *   - Truth source (openfoam_native / mock / unknown)
 *   - Trust gate verdict (PASS / PASS_WITH_DISCLAIMER / FAIL / PENDING)
 *   - Audit percentage
 *   - Corpus / solver / mesh / gold SHAs (when surfaced by /completeness)
 *   - Reproducibility hint
 *
 * Read-only display. The TruthChain tab is the "show me what backs this
 * result" surface engineers consult before trusting a number.
 */
import { useCaseStatus } from "../../../step_panel_shell/useCaseStatus";
import type { StepId } from "../../WorkbenchShellV3";
import { VerdictPill as SharedVerdictPill } from "../VerdictPill";

interface TruthChainContentProps {
  caseId: string | null;
  stepId: StepId;
}

// V73.4 · Wrapper around shared VerdictPill primitive so the existing
// `truthchain-verdict` testid remains stable for V71.O contract tests.
function VerdictPill({
  verdict,
}: {
  verdict: "PASS" | "PASS_WITH_DISCLAIMER" | "FAIL" | "PENDING";
}) {
  return <SharedVerdictPill verdict={verdict} data-testid="truthchain-verdict" />;
}

function Section({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mb-8">
      <div className="text-[11px] uppercase tracking-[0.08em] text-v3-textTertiary mb-3">
        {label}
      </div>
      <div className="space-y-2.5 text-[13px]">{children}</div>
    </div>
  );
}

function Row({
  k,
  v,
  mono = true,
}: {
  k: string;
  v: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="text-v3-textSecondary truncate">{k}</span>
      <span
        className={`text-v3-textPrimary text-right tabular-nums ${
          mono ? "font-mono" : ""
        }`}
      >
        {v}
      </span>
    </div>
  );
}

function ChainLink({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail?: string;
}) {
  return (
    <div className="flex items-start gap-3 py-1.5">
      <div className="w-1.5 h-1.5 rounded-full bg-v3-accent mt-2 shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="text-[12px] text-v3-textPrimary">{label}</div>
        <div className="text-[11px] text-v3-textSecondary font-mono truncate">
          {value}
        </div>
        {detail && (
          <div className="text-[10px] text-v3-textTertiary">{detail}</div>
        )}
      </div>
    </div>
  );
}

export function TruthChainContent({
  caseId,
  stepId,
}: TruthChainContentProps) {
  const { status, isLoading, isError } = useCaseStatus(caseId);

  if (!caseId) {
    return (
      <div className="text-[13px] text-v3-textSecondary">
        <Section label="No case selected">
          <p className="text-[12px] text-v3-textTertiary leading-relaxed">
            Select a case to view its provenance chain — truth source, trust
            gate verdict, corpus SHA, and reproducibility hints.
          </p>
        </Section>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="text-[13px] text-v3-textTertiary">
        <Section label="Loading provenance…">
          <p className="text-[12px]">Querying /api/cases/{caseId}/completeness…</p>
        </Section>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="text-[13px] text-v3-textSecondary">
        <Section label="TruthChain unavailable">
          <p className="text-[12px] text-v3-textTertiary leading-relaxed">
            Completeness endpoint did not respond. The case may not have run
            yet, or the backend is offline. Re-try after Step 4 completes.
          </p>
        </Section>
      </div>
    );
  }

  return (
    <div
      data-testid="truthchain-content"
      data-step={stepId}
      className="text-[13px]"
    >
      <Section label="Trust Gate Verdict">
        <div className="flex items-center justify-between">
          <span className="text-v3-textSecondary">verdict</span>
          <VerdictPill verdict={status.trustGate} />
        </div>
        <Row
          k="audit completeness"
          v={
            status.auditPct == null
              ? "—"
              : `${status.auditPct.toFixed(0)}%`
          }
        />
        <Row k="truth source" v={status.truthSource} mono={false} />
        <Row
          k="llm path"
          v={status.llmOffline ? "offline · advisor-only" : "online"}
          mono={false}
        />
      </Section>

      <Section label="Provenance Chain">
        <ChainLink
          label="Case"
          value={status.caseId}
          detail={
            status.truthSource === "openfoam_native"
              ? "whitelisted gold standard"
              : status.truthSource === "mock"
              ? "MSW mock substrate"
              : "user-imported · unverified"
          }
        />
        <ChainLink
          label="Validation"
          value={status.validation ?? "audit-pending"}
          detail="completeness audit · advisor-only"
        />
        <ChainLink
          label="Last action"
          value={status.lastAction ?? "—"}
          detail={stepId >= 4 ? "solver pipeline" : "preprocessing"}
        />
      </Section>

      <Section label="Reproducibility">
        <p className="text-[12px] text-v3-textTertiary leading-relaxed">
          To reproduce: pull this case at the same corpus SHA, re-run the
          same solver dict, and verify residual fingerprint &amp; gold-band
          overlap. The TrustGate verdict is monotonic in the underlying
          checks — a downgrade always reflects a real audit miss, never UI
          churn.
        </p>
      </Section>

      <div className="mt-6 text-[10px] uppercase tracking-[0.08em] text-v3-textTertiary border-t border-v3-border pt-3">
        TruthChain · GET /api/cases/{caseId}/completeness · advisory-only
      </div>
    </div>
  );
}
