import type { Precondition } from "@/types/validation";

interface Props {
  preconditions: Precondition[];
}

export function PreconditionList({ preconditions }: Props) {
  if (!preconditions.length) {
    return (
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Physics Preconditions</h3>
        </div>
        <p className="px-4 py-6 text-sm text-surface-400">
          No physics preconditions declared for this case.
        </p>
      </div>
    );
  }
  const unsatisfiedCount = preconditions.filter((p) => !p.satisfied).length;
  return (
    <div className="card">
      <div className="card-header flex items-center justify-between">
        <h3 className="card-title">Physics Preconditions</h3>
        <span
          className={`text-xs ${unsatisfiedCount ? "text-contract-hazard" : "text-contract-pass"}`}
        >
          {preconditions.length - unsatisfiedCount}/{preconditions.length} satisfied
        </span>
      </div>
      <ul className="divide-y divide-surface-700">
        {preconditions.map((p, idx) => (
          <li key={idx} className="px-4 py-3">
            <div className="flex items-start gap-3">
              <span
                className={`mt-0.5 inline-block h-2 w-2 shrink-0 rounded-full ${p.satisfied ? "bg-contract-pass" : "bg-contract-hazard"}`}
                aria-hidden
              />
              <div className="flex-1">
                <p className="text-sm text-surface-100">{p.condition}</p>
                {p.evidence_ref && (
                  <p className="mt-1 text-[11px] text-surface-400">
                    <span className="font-semibold text-surface-300">
                      Evidence:
                    </span>{" "}
                    {p.evidence_ref}
                  </p>
                )}
                {!p.satisfied && p.consequence_if_unsatisfied && (
                  <p className="mt-1 text-[11px] text-contract-hazard">
                    <span className="font-semibold">Consequence:</span>{" "}
                    {p.consequence_if_unsatisfied}
                  </p>
                )}
              </div>
              <span
                className={`mono text-[10px] font-semibold uppercase ${p.satisfied ? "text-contract-pass" : "text-contract-hazard"}`}
              >
                {p.satisfied ? "satisfied" : "unmet"}
              </span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
