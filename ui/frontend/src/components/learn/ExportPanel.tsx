// ExportPanel · Stage 6 ExportPack MVP — dual-format export cards
// (PDF + CSV) + lightweight manifest summary. Per Codex industrial-
// workbench meeting 2026-04-25 + roadmap S6.
//
// Two surfaces:
//
// 1. <ExportPanel /> (no props) — system-level batch export. Shows
//    schema version, column count, batch row count. CSV download
//    button hits `/api/exports/batch.csv`. Sits on LearnHomePage
//    below the BatchMatrix.
//
// 2. <RunExportPanel caseId runLabel /> — per-(case, run) compact
//    card. Two download buttons: PDF (existing comparison-report
//    endpoint) + CSV (new). Sits in Pro Workbench / case detail
//    surfaces where a single run is in focus. (Wired in this commit
//    to LearnHomePage only via the system-level panel; per-run
//    exports stay reachable via direct URL until a per-case wire-in
//    is requested.)
//
// CSV-vs-xlsx note: Stage 6 spec says xlsx but the runtime has no
// openpyxl. CSV is functionally equivalent for audit (opens in
// Excel/Sheets natively, fully grep-able). Future xlsx upgrade is
// a one-line change when openpyxl lands. Schema (34 columns) is
// version-stable and forward-compat — adding columns won't break
// downstream consumers.

import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import type { ExportManifest } from "@/types/exports";

export function ExportPanel() {
  const { data, error, isLoading } = useQuery<ExportManifest>({
    queryKey: ["export-manifest"],
    queryFn: () => api.getExportManifest(),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="h-[140px] animate-pulse rounded-md border border-surface-800 bg-surface-900/40" />
    );
  }
  if (error || !data) {
    return null;
  }

  return (
    <section className="rounded-lg border border-surface-800 bg-surface-950/40 p-5">
      <div className="mb-3 flex items-baseline justify-between">
        <div>
          <h2 className="card-title">导出 · Audit Pack</h2>
          <p className="mt-1 text-[12px] text-surface-500">
            完整 fixture 表格 — 把 case × run × observable × verdict 一次性下载。
            可在 Excel / Google Sheets / pandas 直接打开，便于审计员独立复核。
          </p>
        </div>
        <span className="mono text-[10px] uppercase tracking-wider text-surface-600">
          exports · {data.schema_version}
        </span>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {/* CSV card */}
        <DownloadCard
          format="CSV"
          variant="primary"
          title="批量 fixture 导出"
          subtitle={`${data.n_batch_rows} rows × ${data.n_columns} columns`}
          href="/api/exports/batch.csv"
          download="cfd-harness_batch_export.csv"
          ready={true}
          tone="本格式：纯 stdlib 序列化 · audit 友好（grep-able）"
        />
        {/* PDF batch card — placeholder pointing into Pro Workbench since
            there's no batch PDF yet; per-run PDF stays in the Pro path. */}
        <DownloadCard
          format="PDF"
          variant="secondary"
          title="单 run 报告（Pro Workbench）"
          subtitle="per-(case, run) PDF · 现已上线"
          href="/audit-package"
          download={null}
          ready={true}
          tone="完整签名审计包 · HMAC manifest + comparison-report.pdf"
        />
      </div>

      {/* Manifest summary strip */}
      <div className="mt-4 grid gap-2 rounded-sm border border-surface-800 bg-surface-950 p-3 text-[11px] sm:grid-cols-4">
        <ManifestField label="schema" value={data.schema_version} />
        <ManifestField label="columns" value={String(data.n_columns)} />
        <ManifestField label="batch rows" value={String(data.n_batch_rows)} />
        <ManifestField label="exporter" value={data.exporter} />
      </div>

      <p className="mt-3 text-[11px] leading-relaxed text-surface-500">
        <strong className="text-surface-400">字段清单：</strong>
        {data.columns.slice(0, 10).join(" · ")}
        <span className="text-surface-700">
          {" "}
          + {data.columns.length - 10} 项（看 manifest）
        </span>
      </p>
    </section>
  );
}

// Per-run mini panel — exported for future use in Pro Workbench page.

export function RunExportPanel({
  caseId,
  runId,
}: {
  caseId: string;
  runId: string;
}) {
  const csvHref = `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(runId)}/export.csv`;
  const pdfHref = `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(runId)}/comparison-report.pdf`;
  return (
    <div className="grid gap-2 rounded-md border border-surface-800 bg-surface-900/40 p-3 sm:grid-cols-2">
      <a
        href={csvHref}
        download={`${caseId}_${runId}.csv`}
        className="group inline-flex items-center justify-between gap-2 rounded-sm border border-emerald-900/50 bg-emerald-950/30 px-3 py-2 text-[12px] text-emerald-200 hover:border-emerald-700/60 hover:bg-emerald-950/50"
      >
        <span>
          <span className="mono mr-2 text-[10px] uppercase tracking-wider text-emerald-500">
            CSV
          </span>
          单 run 表格导出
        </span>
        <span className="mono text-[10px] text-emerald-400 group-hover:text-emerald-300">
          ↓
        </span>
      </a>
      <a
        href={pdfHref}
        className="group inline-flex items-center justify-between gap-2 rounded-sm border border-sky-900/50 bg-sky-950/30 px-3 py-2 text-[12px] text-sky-200 hover:border-sky-700/60 hover:bg-sky-950/50"
      >
        <span>
          <span className="mono mr-2 text-[10px] uppercase tracking-wider text-sky-500">
            PDF
          </span>
          comparison report
        </span>
        <span className="mono text-[10px] text-sky-400 group-hover:text-sky-300">
          ↓
        </span>
      </a>
    </div>
  );
}

// --- Internals ----------------------------------------------------------

function DownloadCard({
  format,
  variant,
  title,
  subtitle,
  href,
  download,
  ready,
  tone,
}: {
  format: string;
  variant: "primary" | "secondary";
  title: string;
  subtitle: string;
  href: string;
  download: string | null;
  ready: boolean;
  tone: string;
}) {
  const palette =
    variant === "primary"
      ? "border-emerald-900/50 bg-emerald-950/25 hover:border-emerald-700/60"
      : "border-sky-900/50 bg-sky-950/25 hover:border-sky-700/60";
  const tag =
    variant === "primary"
      ? "bg-emerald-900/60 text-emerald-200"
      : "bg-sky-900/60 text-sky-200";
  const status =
    variant === "primary"
      ? "text-emerald-300"
      : "text-sky-300";

  return (
    <a
      href={href}
      {...(download ? { download } : {})}
      target={download ? undefined : "_self"}
      className={`group flex flex-col rounded-md border ${palette} p-4 transition-colors`}
    >
      <div className="flex items-start justify-between">
        <span className={`mono rounded-sm px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider ${tag}`}>
          {format}
        </span>
        {ready && (
          <span className={`mono text-[10px] ${status}`}>● ready</span>
        )}
      </div>
      <p className="mt-3 text-[14px] font-medium text-surface-100">{title}</p>
      <p className="mt-1 text-[11px] text-surface-400">{subtitle}</p>
      <p className="mt-3 text-[11px] leading-relaxed text-surface-500">{tone}</p>
      <span className={`mono mt-3 text-[11px] ${status} group-hover:underline`}>
        {download ? "↓ download" : "→ open in workbench"}
      </span>
    </a>
  );
}

function ManifestField({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <span className="mono text-[10px] uppercase tracking-wider text-surface-500">
        {label}
      </span>
      <span className="mono text-surface-200">{value}</span>
    </div>
  );
}
