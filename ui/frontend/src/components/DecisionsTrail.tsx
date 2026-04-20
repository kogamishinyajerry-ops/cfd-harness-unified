import type { DecisionLink } from "@/types/validation";

interface Props {
  decisions: DecisionLink[];
}

export function DecisionsTrail({ decisions }: Props) {
  if (!decisions.length) {
    return (
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Decisions Trail</h3>
        </div>
        <p className="px-4 py-6 text-sm text-surface-400">
          No decisions recorded against this measurement yet.
        </p>
      </div>
    );
  }
  return (
    <div className="card">
      <div className="card-header flex items-center justify-between">
        <h3 className="card-title">Decisions Trail</h3>
        <span className="text-xs text-surface-400">
          {decisions.length} linked
        </span>
      </div>
      <ol className="divide-y divide-surface-700">
        {decisions.map((d) => (
          <li key={d.decision_id} className="px-4 py-3">
            <div className="flex items-baseline gap-3">
              <code className="mono text-[11px] text-surface-200">
                {d.decision_id}
              </code>
              <span className="mono text-[10px] text-surface-400">
                {d.date}
              </span>
              <span
                className={`text-[10px] font-semibold uppercase tracking-wider ${
                  d.autonomous ? "text-contract-hazard" : "text-contract-pass"
                }`}
              >
                {d.autonomous ? "autonomous" : "externally approved"}
              </span>
            </div>
            <p className="mt-1 text-sm text-surface-100">{d.title}</p>
          </li>
        ))}
      </ol>
    </div>
  );
}
