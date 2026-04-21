import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { api, ApiError } from "@/api/client";
import { AuditConcernList } from "@/components/AuditConcernList";
import { BandChart } from "@/components/BandChart";
import { DecisionsTrail } from "@/components/DecisionsTrail";
import { PassFailChip } from "@/components/PassFailChip";
import { PreconditionList } from "@/components/PreconditionList";
import type { ValidationReport } from "@/types/validation";

export function ValidationReportPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const { data, error, isLoading } = useQuery<ValidationReport>({
    queryKey: ["validation-report", caseId],
    queryFn: () => api.getValidationReport(caseId!),
    enabled: Boolean(caseId),
  });

  if (isLoading) {
    return (
      <div className="mx-auto max-w-5xl px-6 py-8">
        <div className="card p-8">
          <div className="animate-pulse space-y-4">
            <div className="h-6 w-1/3 rounded-sm bg-surface-800" />
            <div className="h-4 w-2/3 rounded-sm bg-surface-800" />
            <div className="h-32 rounded-sm bg-surface-800" />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    const status = error instanceof ApiError ? error.status : 500;
    return (
      <div className="mx-auto max-w-5xl px-6 py-8">
        <div className="card p-6">
          <p className="text-contract-fail">
            Could not load report for <code className="mono">{caseId}</code>{" "}
            (HTTP {status}).
          </p>
          <Link
            to="/cases"
            className="mt-3 inline-block text-xs text-surface-300 underline-offset-2 hover:underline"
          >
            ← back to cases
          </Link>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const { case: caseDetail, gold_standard: gs, measurement } = data;

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <nav className="mb-4 text-xs text-surface-400">
        <Link to="/cases" className="hover:text-surface-200">
          Cases
        </Link>
        <span className="mx-2 text-surface-600">/</span>
        <span className="text-surface-200">{caseDetail.case_id}</span>
        <span className="mx-2 text-surface-600">/</span>
        <span>Validation Report</span>
      </nav>

      <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-surface-400">
            Validation Report
          </p>
          <h1 className="text-2xl font-semibold text-surface-100">
            {caseDetail.name}
          </h1>
          <p className="mt-1 text-xs text-surface-400">
            {caseDetail.reference ?? "(no literature reference on file)"}{" "}
            {caseDetail.doi && (
              <>
                · DOI <code className="mono">{caseDetail.doi}</code>
              </>
            )}
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <PassFailChip status={data.contract_status} size="lg" />
          <Link
            to={`/audit-package?case=${encodeURIComponent(caseDetail.case_id)}&run=audit_real_run`}
            className="rounded-sm border border-accent-600/50 bg-accent-600/10 px-3 py-1.5 text-xs font-medium text-accent-300 hover:border-accent-500 hover:bg-accent-600/20"
            title="Build signed audit package from the real-solver audit_real_run fixture"
          >
            签名审计包 ↓
          </Link>
        </div>
      </header>

      {/* Top row: measurement/ref card + band chart */}
      <section className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-5">
        <div className="card md:col-span-2">
          <div className="card-header">
            <h3 className="card-title">Measurement vs. Gold Standard</h3>
          </div>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-3 px-4 py-4 text-sm">
            <dt className="text-surface-400">Quantity</dt>
            <dd className="text-surface-100">{gs.quantity}</dd>

            <dt className="text-surface-400">Gold ref</dt>
            <dd className="mono text-surface-100">
              {gs.ref_value} {gs.unit}
            </dd>

            <dt className="text-surface-400">Tolerance</dt>
            <dd className="mono text-surface-100">
              ±{(gs.tolerance_pct * 100).toFixed(1)}%
            </dd>

            <dt className="text-surface-400">Band</dt>
            <dd className="mono text-surface-200">
              [{data.tolerance_lower.toPrecision(4)}, {data.tolerance_upper.toPrecision(4)}]
            </dd>

            <dt className="text-surface-400">Measurement</dt>
            <dd className="mono text-surface-100">
              {measurement
                ? `${measurement.value} ${measurement.unit}`
                : "— (no run)"}
            </dd>

            <dt className="text-surface-400">Deviation</dt>
            <dd className="mono text-surface-100">
              {data.deviation_pct === null
                ? "—"
                : `${data.deviation_pct.toFixed(2)}%`}
            </dd>

            <dt className="text-surface-400">Within band</dt>
            <dd className="text-surface-100">
              {data.within_tolerance === null
                ? "—"
                : data.within_tolerance
                  ? "yes"
                  : "no"}
            </dd>

            <dt className="text-surface-400">Citation</dt>
            <dd className="text-[12px] text-surface-200">{gs.citation}</dd>
          </dl>
        </div>

        <div className="card md:col-span-3">
          <div className="card-header">
            <h3 className="card-title">Tolerance Band</h3>
          </div>
          <div className="px-4 py-4">
            <BandChart
              refValue={gs.ref_value}
              lower={data.tolerance_lower}
              upper={data.tolerance_upper}
              measurement={measurement?.value ?? null}
              unit={gs.unit}
              status={data.contract_status}
            />
          </div>
        </div>
      </section>

      {/* Provenance strip — small-text run metadata */}
      {measurement && (
        <section className="mb-6 card px-4 py-3 text-[11px] text-surface-300">
          <span className="font-semibold uppercase tracking-wider text-surface-400">
            Provenance ·{" "}
          </span>
          <span className="mono">
            source={measurement.source} · run_id=
            {measurement.run_id ?? "—"} · commit=
            {measurement.commit_sha ?? "—"} · at=
            {measurement.measured_at ?? "—"}
          </span>
        </section>
      )}

      {/* Three-column lower grid */}
      <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <AuditConcernList concerns={data.audit_concerns} />
        <PreconditionList preconditions={data.preconditions} />
      </section>
      <section className="mt-4">
        <DecisionsTrail decisions={data.decisions_trail} />
      </section>

      {caseDetail.contract_status_narrative && (
        <section className="mt-6 card">
          <div className="card-header">
            <h3 className="card-title">Contract-status narrative</h3>
          </div>
          <pre className="whitespace-pre-wrap px-4 py-4 text-[12px] leading-relaxed text-surface-200">
            {caseDetail.contract_status_narrative}
          </pre>
        </section>
      )}
    </div>
  );
}
