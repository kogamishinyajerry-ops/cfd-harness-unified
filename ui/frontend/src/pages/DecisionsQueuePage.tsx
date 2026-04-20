import { useQuery } from "@tanstack/react-query";

import { api, ApiError } from "@/api/client";
import type { DecisionCard, DecisionColumn } from "@/types/decisions";

// Phase 2 — Decisions Queue. Kanban 4-column read-only view of
// .planning/decisions/*.md backed by /api/decisions. Includes a
// side panel for the external Gate queue (Q-1 / Q-2 / Q-3).

const COLUMNS: { key: DecisionColumn; title: string; hint: string }[] = [
  { key: "Accepted",   title: "Accepted",   hint: "Mirrored to Notion, live" },
  { key: "Closed",     title: "Closed",     hint: "Self-approve or auto-resolve" },
  { key: "Open",       title: "Open",       hint: "Awaiting review / sync" },
  { key: "Superseded", title: "Superseded", hint: "Replaced by a later DEC" },
];

function GateDot({ state }: { state: "OPEN" | "CLOSED" }) {
  const color = state === "OPEN" ? "bg-contract-hazard" : "bg-contract-pass";
  return <span aria-hidden className={`inline-block h-1.5 w-1.5 rounded-full ${color}`} />;
}

function DecisionCardView({ card }: { card: DecisionCard }) {
  return (
    <article className="rounded-md border border-surface-800 bg-surface-900/50 p-3 space-y-1.5 transition hover:border-surface-700">
      <header className="flex items-baseline justify-between gap-2">
        <h3 className="text-xs font-mono font-semibold text-surface-100">{card.decision_id}</h3>
        <span className="text-[10px] text-surface-500">{card.timestamp.slice(0, 10)}</span>
      </header>
      <p className="text-[13px] leading-snug text-surface-200">{card.title}</p>
      {card.scope && (
        <p className="text-[10px] uppercase tracking-wider text-surface-500">scope: {card.scope}</p>
      )}
      <div className="flex flex-wrap gap-1.5 pt-1 text-[10px]">
        {card.autonomous && (
          <span className="rounded-sm bg-surface-800 px-1.5 py-0.5 text-surface-300">autonomous</span>
        )}
        {card.superseded_by && (
          <span className="rounded-sm bg-surface-800 px-1.5 py-0.5 text-surface-400">
            superseded by {card.superseded_by}
          </span>
        )}
      </div>
      {(card.notion_url || card.github_pr_url) && (
        <div className="flex gap-2 pt-1 text-[10px]">
          {card.notion_url && (
            <a
              href={card.notion_url}
              target="_blank"
              rel="noreferrer noopener"
              className="text-surface-400 underline-offset-2 hover:text-surface-200 hover:underline"
            >
              Notion ↗
            </a>
          )}
          {card.github_pr_url && (
            <a
              href={card.github_pr_url}
              target="_blank"
              rel="noreferrer noopener"
              className="text-surface-400 underline-offset-2 hover:text-surface-200 hover:underline"
            >
              PR ↗
            </a>
          )}
          <code className="ml-auto truncate text-surface-500" title={card.relative_path}>
            {card.relative_path.replace(".planning/decisions/", "")}
          </code>
        </div>
      )}
    </article>
  );
}

export function DecisionsQueuePage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["decisions"],
    queryFn: api.listDecisions,
  });

  if (isLoading) {
    return <section className="px-8 py-10 text-surface-300">Loading decisions…</section>;
  }
  if (isError || !data) {
    const msg = error instanceof ApiError ? `${error.status}: ${error.message}` : String(error);
    return (
      <section className="px-8 py-10">
        <div className="rounded-md border border-contract-fail/40 bg-contract-fail/10 px-4 py-3 text-sm text-contract-fail">
          Failed to load decisions: {msg}
        </div>
      </section>
    );
  }

  const byColumn: Record<DecisionColumn, DecisionCard[]> = {
    Accepted: [], Closed: [], Open: [], Superseded: [],
  };
  for (const c of data.cards) byColumn[c.column].push(c);

  return (
    <section className="p-8">
      <header className="mb-6 flex items-baseline justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-surface-100">Decisions Queue</h1>
          <p className="mt-1 text-sm text-surface-400">
            Kanban view of <code>.planning/decisions/*.md</code>. Notion column reflects sync state;
            external Gate items are tracked separately (right panel).
          </p>
        </div>
        <div className="text-[11px] text-surface-500">
          total: <strong className="text-surface-200">{data.cards.length}</strong>
        </div>
      </header>

      <div className="grid grid-cols-[1fr_1fr_1fr_1fr_320px] gap-4">
        {COLUMNS.map((col) => (
          <div key={col.key} className="flex min-h-[280px] flex-col">
            <header className="mb-2 flex items-baseline justify-between border-b border-surface-800 pb-1">
              <h2 className="text-sm font-semibold text-surface-100">{col.title}</h2>
              <span className="text-[10px] text-surface-500">{byColumn[col.key].length}</span>
            </header>
            <p className="mb-2 text-[10px] text-surface-500">{col.hint}</p>
            <div className="space-y-2">
              {byColumn[col.key].length === 0 ? (
                <p className="text-xs text-surface-600">— empty —</p>
              ) : (
                byColumn[col.key].map((card) => (
                  <DecisionCardView key={card.decision_id + card.relative_path} card={card} />
                ))
              )}
            </div>
          </div>
        ))}

        <aside className="rounded-md border border-surface-800 bg-surface-900/40 p-4">
          <header className="mb-3 flex items-baseline justify-between border-b border-surface-800 pb-1">
            <h2 className="text-sm font-semibold text-surface-100">External Gate Queue</h2>
            <span className="text-[10px] text-surface-500">{data.gate_queue.length}</span>
          </header>
          <p className="mb-3 text-[10px] text-surface-500">
            Items that autonomous governance deferred to external review.
          </p>
          <ul className="space-y-2.5">
            {data.gate_queue.map((g) => (
              <li key={g.qid} className="rounded-sm bg-surface-950/40 p-2.5 text-[12px]">
                <div className="flex items-center gap-1.5 text-surface-200">
                  <GateDot state={g.state} />
                  <strong className="font-mono">{g.qid}</strong>
                  <span className="ml-auto text-[10px] uppercase tracking-wider text-surface-500">{g.state}</span>
                </div>
                <p className="mt-1 text-surface-300">{g.title}</p>
                {g.summary && (
                  <p className="mt-1 text-[11px] text-surface-500">{g.summary}</p>
                )}
              </li>
            ))}
          </ul>
        </aside>
      </div>
    </section>
  );
}
