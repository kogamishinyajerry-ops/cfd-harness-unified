import type { AuditConcern } from "@/types/validation";

// Audit concerns surface — the commercial differentiator of the product.
// Each row exposes:
//   - concern_type: canonical token (SILENT_PASS_HAZARD / DEVIATION / ...)
//   - summary: one-liner rendered prominently
//   - detail: collapsible <details> so the audit package has no
//     hidden-by-default content (regulator review flag)
//   - decision_refs: DEC-XXX tokens styled as pills linking back to
//     the decisions trail below.

const TYPE_STYLES: Record<string, { label: string; color: string }> = {
  COMPATIBLE_WITH_SILENT_PASS_HAZARD: {
    label: "Silent-Pass Hazard",
    color: "text-contract-hazard",
  },
  CONTRACT_STATUS: { label: "Contract Status", color: "text-surface-100" },
  DEVIATION: { label: "Deviation", color: "text-contract-fail" },
  UNKNOWN: { label: "Concern", color: "text-surface-200" },
};

interface Props {
  concerns: AuditConcern[];
}

export function AuditConcernList({ concerns }: Props) {
  if (!concerns.length) {
    return (
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Audit Concerns</h3>
        </div>
        <p className="px-4 py-6 text-sm text-surface-400">
          No audit concerns surfaced for this run.
        </p>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header flex items-center justify-between">
        <h3 className="card-title">Audit Concerns</h3>
        <span className="text-xs text-surface-400">
          {concerns.length} surfaced
        </span>
      </div>
      <ul className="divide-y divide-surface-700">
        {concerns.map((c, idx) => {
          const style = TYPE_STYLES[c.concern_type] ?? TYPE_STYLES.UNKNOWN;
          return (
            <li key={`${c.concern_type}-${idx}`} className="px-4 py-3">
              <div className="flex items-baseline gap-3">
                <span
                  className={`text-[10px] font-semibold uppercase tracking-widest ${style.color}`}
                >
                  {style.label}
                </span>
                <code className="mono text-[10px] text-surface-400">
                  {c.concern_type}
                </code>
              </div>
              <p className="mt-1 text-sm text-surface-100">{c.summary}</p>
              {c.detail && (
                <details className="mt-2">
                  <summary className="cursor-pointer text-xs text-surface-300 hover:text-surface-100">
                    Show detail
                  </summary>
                  <p className="mt-2 whitespace-pre-wrap rounded-sm bg-surface-800 px-3 py-2 text-[12px] text-surface-200">
                    {c.detail}
                  </p>
                </details>
              )}
              {c.decision_refs.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {c.decision_refs.map((ref) => (
                    <span
                      key={ref}
                      className="mono rounded-sm bg-surface-700 px-1.5 py-0.5 text-[10px] text-surface-200"
                    >
                      {ref}
                    </span>
                  ))}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
