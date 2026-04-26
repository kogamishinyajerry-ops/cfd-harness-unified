import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api, ApiError } from "@/api/client";
import type { RunDetail } from "@/types/run_history";
import { FAILURE_CATEGORY_LABEL_ZH } from "@/types/run_history";

// M3 · Workbench Closed-Loop main-line — /workbench/case/:caseId/run/:runId
//
// Detail view for a single run. Surfaces the contents of the three
// per-run artifacts (measurement.yaml, verdict.json, summary.json) without
// trying to be the audit-package builder — that's the existing pro
// /audit-package surface. This page is the "did my Re=400 LDC pass?"
// glance that follows up a run from /workbench/case/:caseId/edit.

export function RunDetailPage() {
  const { caseId = "", runId = "" } = useParams<{ caseId: string; runId: string }>();
  const detailQuery = useQuery({
    queryKey: ["workbenchRunDetail", caseId, runId],
    queryFn: () => api.getRunDetail(caseId, runId),
    enabled: Boolean(caseId) && Boolean(runId),
  });

  if (!caseId || !runId) {
    return <Section><p className="text-sm text-contract-fail">missing path params</p></Section>;
  }
  if (detailQuery.isLoading) {
    return <Section><p className="text-surface-300">Loading run {runId}…</p></Section>;
  }
  if (detailQuery.isError || !detailQuery.data) {
    const msg =
      detailQuery.error instanceof ApiError
        ? `${detailQuery.error.status}: ${detailQuery.error.message}`
        : String(detailQuery.error);
    return (
      <Section>
        <p className="text-sm text-contract-fail">Failed to load run detail: {msg}</p>
      </Section>
    );
  }

  const d = detailQuery.data;

  return (
    <Section>
      <header className="mb-6">
        <div className="text-[11px] uppercase tracking-wider text-surface-500">
          <Link to="/learn" className="hover:text-surface-300">Learn</Link>
          <span className="mx-1.5">/</span>
          <Link to={`/learn/cases/${caseId}`} className="hover:text-surface-300">{caseId}</Link>
          <span className="mx-1.5">/</span>
          <Link
            to={`/workbench/case/${encodeURIComponent(caseId)}/runs`}
            className="hover:text-surface-300"
          >
            runs
          </Link>
          <span className="mx-1.5">/</span>
          <span className="font-mono">{runId}</span>
        </div>
        <h1 className="mt-1 text-2xl font-semibold text-surface-100">
          Run · <span className="font-mono text-[18px]">{runId}</span>
        </h1>
      </header>

      <VerdictCard d={d} />

      {!d.success && d.failure_category && (
        <FailureBanner category={d.failure_category} remediation={d.failure_remediation} />
      )}

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Block title="Task spec (excerpt)">
          <KvList obj={d.task_spec} />
          <div className="mt-3 text-[10px] text-surface-500">
            source = <code className="font-mono">{d.source_origin}</code>
            {d.source_origin === "draft" && (
              <span className="ml-2">
                (loaded from <code>ui/backend/user_drafts/{caseId}.yaml</code>)
              </span>
            )}
          </div>
        </Block>

        <Block title="Key quantities">
          {Object.keys(d.key_quantities).length === 0 ? (
            <p className="text-xs text-surface-500">— none extracted —</p>
          ) : (
            <KvList obj={d.key_quantities} numericOnly={false} />
          )}
        </Block>

        <Block title="Residuals (final)">
          {Object.keys(d.residuals).length === 0 ? (
            <p className="text-xs text-surface-500">— none reported —</p>
          ) : (
            <ul className="space-y-1 font-mono text-[12px]">
              {Object.entries(d.residuals).map(([k, v]) => (
                <li key={k} className="flex justify-between text-surface-300">
                  <span>{k}</span>
                  <span>{v.toExponential(2)}</span>
                </li>
              ))}
            </ul>
          )}
        </Block>

        <Block title="Timestamps">
          <KvList
            obj={{
              started_at: d.started_at,
              ended_at: d.ended_at,
              duration_s: d.duration_s.toFixed(2),
            }}
          />
        </Block>
      </div>

      {d.error_message && (
        <div className="mt-6 rounded-md border border-contract-fail/40 bg-contract-fail/5 p-4">
          <h3 className="mb-2 text-[11px] uppercase tracking-wider text-contract-fail">
            Error message
          </h3>
          <pre className="whitespace-pre-wrap font-mono text-[12px] text-contract-fail/90">
            {d.error_message}
          </pre>
        </div>
      )}

      <div className="mt-8 flex flex-wrap gap-3">
        <Link
          to={`/workbench/case/${encodeURIComponent(caseId)}/edit`}
          className="rounded-sm border border-surface-700 bg-surface-900/40 px-3 py-1.5 text-xs text-surface-300 transition hover:bg-surface-800"
        >
          ← Back to params
        </Link>
        <Link
          to={`/workbench/case/${encodeURIComponent(caseId)}/runs`}
          className="rounded-sm border border-surface-700 bg-surface-900/40 px-3 py-1.5 text-xs text-surface-300 transition hover:bg-surface-800"
        >
          ← All runs for this case
        </Link>
        <Link
          to={`/cases/${caseId}/report`}
          className="rounded-sm border border-surface-700 bg-surface-900/40 px-3 py-1.5 text-xs text-surface-300 transition hover:bg-surface-800"
        >
          Pro validation report →
        </Link>
      </div>
    </Section>
  );
}

function Section({ children }: { children: React.ReactNode }) {
  return <section className="mx-auto max-w-6xl px-8 py-8">{children}</section>;
}

function VerdictCard({ d }: { d: RunDetail }) {
  const tone = d.success
    ? "border-contract-pass/40 bg-contract-pass/5 text-contract-pass"
    : "border-contract-fail/40 bg-contract-fail/5 text-contract-fail";
  return (
    <div className={`rounded-md border p-4 ${tone}`}>
      <div className="text-[10px] uppercase tracking-wider opacity-70">verdict</div>
      <div className="mt-1 text-base font-semibold">
        {d.success ? "PASS" : "FAIL"} · exit_code={d.exit_code} · {d.duration_s.toFixed(1)}s
      </div>
      <div className="mt-1 text-[13px] opacity-90">{d.verdict_summary}</div>
    </div>
  );
}

function FailureBanner({
  category,
  remediation,
}: {
  category: NonNullable<RunDetail["failure_category"]>;
  remediation?: string | null;
}) {
  const label = FAILURE_CATEGORY_LABEL_ZH[category] ?? category;
  return (
    <div className="mt-4 rounded-md border border-amber-500/40 bg-amber-500/5 p-4">
      <div className="text-[10px] uppercase tracking-wider text-amber-400/80">
        failure category
      </div>
      <div className="mt-1 text-base font-semibold text-amber-300">
        {label} <span className="font-mono text-[12px] opacity-70">· {category}</span>
      </div>
      {remediation && (
        <p className="mt-2 whitespace-pre-wrap text-[13px] text-amber-200/90">{remediation}</p>
      )}
    </div>
  );
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-md border border-surface-800 bg-surface-900/40 p-4">
      <h3 className="mb-2 text-[11px] uppercase tracking-wider text-surface-400">{title}</h3>
      {children}
    </div>
  );
}

function KvList({
  obj,
  numericOnly: _numericOnly = false,
}: {
  obj: Record<string, unknown>;
  numericOnly?: boolean;
}) {
  const entries = Object.entries(obj).filter(([, v]) => v !== null && v !== undefined);
  if (entries.length === 0) {
    return <p className="text-xs text-surface-500">—</p>;
  }
  return (
    <dl className="grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 text-[12px]">
      {entries.map(([k, v]) => (
        <FragmentRow key={k} label={k} value={v} />
      ))}
    </dl>
  );
}

function FragmentRow({ label, value }: { label: string; value: unknown }) {
  let display: string;
  if (typeof value === "number") display = String(value);
  else if (typeof value === "string") display = value;
  else if (Array.isArray(value)) display = `[${value.length} items]`;
  else if (typeof value === "object") display = JSON.stringify(value);
  else display = String(value);
  return (
    <>
      <dt className="font-mono text-surface-500">{label}</dt>
      <dd className="font-mono text-surface-200">{display}</dd>
    </>
  );
}
