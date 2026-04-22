import type { Precondition } from "@/types/validation";

interface Props {
  preconditions: Precondition[];
}

type Tone = "pass" | "partial" | "fail";

function toneFor(satisfied: Precondition["satisfied"]): Tone {
  if (satisfied === "partial") return "partial";
  if (satisfied === false) return "fail";
  return "pass";
}

const DOT: Record<Tone, string> = {
  pass: "bg-contract-pass",
  partial: "bg-amber-400",
  fail: "bg-contract-hazard",
};

const LABEL: Record<Tone, string> = {
  pass: "satisfied",
  partial: "partial",
  fail: "unmet",
};

const LABEL_TONE: Record<Tone, string> = {
  pass: "text-contract-pass",
  partial: "text-amber-300",
  fail: "text-contract-hazard",
};

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
  // DEC-V61-046 round-3 R3-B1: tri-state. partial and unmet are both honesty
  // signals but mean different things; the header count separates them.
  const counts = preconditions.reduce(
    (acc, p) => {
      acc[toneFor(p.satisfied)] += 1;
      return acc;
    },
    { pass: 0, partial: 0, fail: 0 } as Record<Tone, number>,
  );
  const headerTone =
    counts.fail > 0
      ? "text-contract-hazard"
      : counts.partial > 0
      ? "text-amber-300"
      : "text-contract-pass";
  const headerParts = [`${counts.pass}/${preconditions.length} satisfied`];
  if (counts.partial) headerParts.push(`${counts.partial} partial`);
  if (counts.fail) headerParts.push(`${counts.fail} unmet`);
  return (
    <div className="card">
      <div className="card-header flex items-center justify-between">
        <h3 className="card-title">Physics Preconditions</h3>
        <span className={`text-xs ${headerTone}`}>
          {headerParts.join(" · ")}
        </span>
      </div>
      <ul className="divide-y divide-surface-700">
        {preconditions.map((p, idx) => {
          const tone = toneFor(p.satisfied);
          return (
            <li key={idx} className="px-4 py-3">
              <div className="flex items-start gap-3">
                <span
                  className={`mt-0.5 inline-block h-2 w-2 shrink-0 rounded-full ${DOT[tone]}`}
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
                  {tone !== "pass" && p.consequence_if_unsatisfied && (
                    <p
                      className={`mt-1 text-[11px] ${tone === "partial" ? "text-amber-300" : "text-contract-hazard"}`}
                    >
                      <span className="font-semibold">Consequence:</span>{" "}
                      {p.consequence_if_unsatisfied}
                    </p>
                  )}
                </div>
                <span
                  className={`mono text-[10px] font-semibold uppercase ${LABEL_TONE[tone]}`}
                >
                  {LABEL[tone]}
                </span>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
