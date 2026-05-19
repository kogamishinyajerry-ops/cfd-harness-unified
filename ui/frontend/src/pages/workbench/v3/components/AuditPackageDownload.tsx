// V74.5 · AuditPackageDownload · industrial-software DNA · the user can
// pull a canonical evidence bundle (manifest + signed zip) on demand.
//
// Flow:
//   1. user clicks the chip · we POST /audit-package/build to materialize
//      the bundle (build_fingerprint deterministic per (case_id, run_id))
//   2. when build returns, we hand the user a GET link to bundle_zip
//
// V130 / V132 contract: building an audit package does NOT mutate the
// case — it materializes a snapshot. No case state is altered. The
// chip carries the standard advisory-only badge alongside.

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { AuditPackageBuildResponse } from "@/types/audit_package";

interface AuditPackageDownloadProps {
  caseId: string;
}

function useLatestRunId(caseId: string) {
  return useQuery({
    queryKey: ["v3-audit-pkg-latest-run", caseId],
    queryFn: () => api.listCaseRuns(caseId),
    enabled: Boolean(caseId),
    staleTime: 30_000,
    retry: 1,
    refetchOnWindowFocus: false,
  });
}

export function AuditPackageDownload({ caseId }: AuditPackageDownloadProps) {
  const { data: runs, isError: runsError } = useLatestRunId(caseId);
  const latest = Array.isArray(runs) && runs.length > 0 ? runs[0] : null;
  const runId = latest?.run_id ?? null;

  const [building, setBuilding] = useState(false);
  const [built, setBuilt] = useState<AuditPackageBuildResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onBuild = async () => {
    if (!runId) return;
    setBuilding(true);
    setError(null);
    try {
      const resp = await api.buildAuditPackage(caseId, runId);
      setBuilt(resp);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "build failed");
    } finally {
      setBuilding(false);
    }
  };

  if (!runId) {
    return (
      <div
        data-testid="audit-package-download-no-run"
        data-source={runsError ? "fallback" : "no-run"}
        className="text-[11px] text-v3-textTertiary leading-relaxed"
      >
        Audit package available after the case has a run. (Run history is
        empty for {caseId}.)
      </div>
    );
  }

  if (built) {
    return (
      <div className="space-y-2">
        <div className="text-[11px] text-v3-textTertiary">
          build_fingerprint{" "}
          <span className="font-mono text-v3-textPrimary">
            {built.build_fingerprint.slice(0, 12)}
          </span>
        </div>
        <a
          data-testid="audit-package-download"
          data-source="live"
          href={built.downloads?.bundle_zip ?? "#"}
          download
          className="inline-flex items-center text-[11px] uppercase tracking-[0.08em] border border-v3-accent rounded px-2 py-1 text-v3-accent motion-safe:transition-colors hover:bg-v3-surface2"
        >
          download · bundle.zip
        </a>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <button
        type="button"
        data-testid="audit-package-build"
        onClick={onBuild}
        disabled={building}
        className="inline-flex items-center text-[11px] uppercase tracking-[0.08em] border border-v3-border rounded px-2 py-1 text-v3-textSecondary motion-safe:transition-colors hover:border-v3-borderActive hover:text-v3-textPrimary disabled:opacity-50"
      >
        {building ? "building…" : "build audit package"}
      </button>
      {error && (
        <div
          data-testid="audit-package-error"
          className="text-[11px] text-v3-wall"
        >
          {error}
        </div>
      )}
      <div className="text-[10px] text-v3-textTertiary leading-relaxed">
        Materializes the canonical evidence bundle for run{" "}
        <span className="font-mono">{runId.slice(0, 12)}</span> · advisory ·
        does not mutate case state.
      </div>
    </div>
  );
}
