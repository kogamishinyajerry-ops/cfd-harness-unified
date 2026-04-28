// Step 1 · Geometry Import — wired body (DEC-V61-096 spec_v2 §E Step 4).
//
// In M-PANELS the actual upload form remains at /workbench/import
// (ImportPage). Once an upload succeeds and the case_id exists, the user
// lands here at /workbench/case/<id>?step=1 where Step 1 is the
// "verify the imported geometry + advance" surface — the shell's center
// pane shows the glb via M-RENDER-API's /geometry/render endpoint, and
// this task panel surfaces the case identity + summary.
//
// The case being addressable already implies Step 1 is complete (the
// import scaffold ran), so we fire onStepComplete on mount via effect.

import { useEffect } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api, ApiError } from "@/api/client";

import type { StepTaskPanelProps } from "../types";

export function Step1Import({ caseId, onStepComplete, onStepError }: StepTaskPanelProps) {
  const caseQuery = useQuery({
    queryKey: ["stepPanelShell", "case", caseId],
    queryFn: () => api.getCase(caseId),
    enabled: caseId.length > 0,
  });

  useEffect(() => {
    if (caseQuery.isSuccess) onStepComplete();
  }, [caseQuery.isSuccess, onStepComplete]);

  useEffect(() => {
    if (caseQuery.isError) {
      const e = caseQuery.error;
      const msg =
        e instanceof ApiError
          ? `${e.status}: ${e.message}`
          : e instanceof Error
          ? e.message
          : String(e);
      onStepError(msg);
    }
  }, [caseQuery.isError, caseQuery.error, onStepError]);

  return (
    <div className="space-y-3 p-3 text-[12px]" data-testid="step1-import-body">
      <h2 className="text-sm font-mono uppercase tracking-wider text-surface-200">
        Step 1 · Geometry import
      </h2>

      {caseQuery.isLoading && (
        <p className="text-surface-500">Loading case…</p>
      )}

      {caseQuery.isError && (
        <p
          data-testid="step1-import-error"
          className="rounded-sm border border-rose-500/40 bg-rose-500/10 px-2 py-1 text-rose-200"
        >
          Failed to load case:{" "}
          {caseQuery.error instanceof ApiError
            ? `${caseQuery.error.status} · ${caseQuery.error.message}`
            : String(caseQuery.error)}
        </p>
      )}

      {caseQuery.isSuccess && (
        <dl
          data-testid="step1-import-summary"
          className="grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 font-mono"
        >
          <dt className="text-surface-500">case_id</dt>
          <dd className="text-surface-200">{caseQuery.data.case_id}</dd>
          <dt className="text-surface-500">name</dt>
          <dd className="text-surface-200">{caseQuery.data.name}</dd>
          <dt className="text-surface-500">geometry</dt>
          <dd className="text-surface-200">{caseQuery.data.geometry_type}</dd>
          <dt className="text-surface-500">flow</dt>
          <dd className="text-surface-200">{caseQuery.data.flow_type}</dd>
        </dl>
      )}

      <p className="rounded-sm border border-surface-800 bg-surface-900/40 px-2 py-1 text-[11px] text-surface-400">
        Geometry rendered above via{" "}
        <code className="font-mono">/api/cases/{caseId}/geometry/render</code>{" "}
        (M-RENDER-API). To upload a different STL, return to the import flow.
      </p>

      <div className="flex items-center justify-end gap-2">
        <Link
          to="/workbench/import"
          data-testid="step1-import-reupload-link"
          className="rounded-sm border border-surface-700 bg-surface-900/40 px-2 py-1 text-[11px] text-surface-300 transition hover:bg-surface-800"
        >
          Re-upload STL →
        </Link>
      </div>
    </div>
  );
}
