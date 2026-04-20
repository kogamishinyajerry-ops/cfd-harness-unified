import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import { PassFailChip } from "@/components/PassFailChip";
import type { CaseIndexEntry } from "@/types/validation";

export function CaseListPage() {
  const { data, isLoading, error } = useQuery<CaseIndexEntry[]>({
    queryKey: ["cases"],
    queryFn: api.listCases,
  });

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <header className="mb-6">
        <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-surface-400">
          Cases
        </p>
        <h1 className="text-2xl font-semibold text-surface-100">
          Whitelist of Validation Cases
        </h1>
        <p className="mt-1 text-sm text-surface-400">
          Canonical cases imported from <code className="mono">knowledge/whitelist.yaml</code>.
          Each row shows the current contract status computed from the
          committed measurement fixture (Phase 0) or the latest run
          (Phase 3+).
        </p>
      </header>

      {isLoading && <Skeleton rows={10} />}
      {error && (
        <div className="card p-4 text-sm text-contract-fail">
          Failed to load cases: {(error as Error).message}
        </div>
      )}
      {data && (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-surface-800 text-left text-[10px] uppercase tracking-wider text-surface-400">
              <tr>
                <th className="px-4 py-2 font-medium">Case</th>
                <th className="px-4 py-2 font-medium">Flow</th>
                <th className="px-4 py-2 font-medium">Turbulence</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">&nbsp;</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-700">
              {data.map((c) => (
                <tr key={c.case_id} className="hover:bg-surface-800/40">
                  <td className="px-4 py-3">
                    <div className="text-surface-100">{c.name}</div>
                    <code className="mono text-[11px] text-surface-400">
                      {c.case_id}
                    </code>
                  </td>
                  <td className="px-4 py-3 text-surface-300">{c.flow_type}</td>
                  <td className="px-4 py-3 text-surface-300">
                    {c.turbulence_model}
                  </td>
                  <td className="px-4 py-3">
                    <PassFailChip status={c.contract_status} size="sm" />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      className="text-xs text-surface-200 underline-offset-2 hover:text-surface-100 hover:underline"
                      to={`/cases/${encodeURIComponent(c.case_id)}/report`}
                    >
                      View Report →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Skeleton({ rows }: { rows: number }) {
  return (
    <div className="card p-4" aria-hidden>
      <div className="animate-pulse space-y-2">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="h-6 rounded-sm bg-surface-800" />
        ))}
      </div>
    </div>
  );
}
