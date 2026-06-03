// Workflow Monitor · panel components (DEC-V61-226)
// --------------------------------------------------
// Self-contained presentational panels for WorkflowMonitorPage. Kept OUT of
// pages/workbench/ (the §11.1-frozen authoring shell) — this is a new run
// OBSERVATION surface, not a fork of the workbench. Pure render-from-props:
// no data fetching here, so the same panels render the mock fixture today and
// a live /api/runs/<id> payload later without change.

import type {
  AdvisorLogEntry,
  MetricVerdict,
  StageState,
  TimelineEntry,
  WorkflowStage,
} from "@/types/workflow";

// ---- state / verdict → tone ------------------------------------------------

const STATE_TONE: Record<
  StageState,
  { label: string; text: string; dot: string; ring: string }
> = {
  pending: { label: "PENDING", text: "text-surface-400", dot: "bg-surface-500", ring: "ring-surface-700" },
  running: { label: "RUNNING", text: "text-sky-300", dot: "bg-sky-400", ring: "ring-sky-500/40" },
  passed: { label: "PASSED", text: "text-contract-pass", dot: "bg-contract-pass", ring: "ring-contract-pass/40" },
  // BLOCKED is the honest "held pending evidence" state — amber/hazard tone,
  // given prominence equal to FAIL (never softened to a quiet warning).
  blocked: { label: "BLOCKED", text: "text-contract-hazard", dot: "bg-contract-hazard", ring: "ring-contract-hazard/50" },
  failed: { label: "FAILED", text: "text-contract-fail", dot: "bg-contract-fail", ring: "ring-contract-fail/50" },
};

const VERDICT_TEXT: Record<MetricVerdict, string> = {
  pass: "text-contract-pass",
  hazard: "text-contract-hazard",
  fail: "text-contract-fail",
  info: "text-surface-300",
};

export function StageStatusBadge({ state }: { state: StageState }) {
  const tone = STATE_TONE[state];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-sm px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] ${tone.text}`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${tone.dot} ${state === "running" ? "animate-pulse" : ""}`}
      />
      {tone.label}
    </span>
  );
}

// ---- left rail · stage flow graph (nodes + connectors) ---------------------

export function StageGraph({
  stages,
  selectedKey,
  currentStage,
  onSelect,
}: {
  stages: WorkflowStage[];
  selectedKey: string;
  currentStage: string;
  onSelect: (key: string) => void;
}) {
  return (
    <nav
      aria-label="Workflow stages"
      className="flex flex-col rounded-md border border-surface-800 bg-surface-900/40 p-3"
    >
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-surface-400">
        Pipeline
      </p>
      <ol className="flex flex-col">
        {stages.map((stage, i) => {
          const tone = STATE_TONE[stage.state];
          const isSelected = stage.key === selectedKey;
          const isCurrent = stage.key === currentStage;
          return (
            <li key={stage.key}>
              <button
                type="button"
                onClick={() => onSelect(stage.key)}
                aria-current={isCurrent ? "step" : undefined}
                className={`flex w-full items-center gap-2.5 rounded-sm px-2 py-2 text-left transition-colors ring-1 ring-inset ${
                  isSelected
                    ? `bg-surface-800 ${tone.ring}`
                    : "ring-transparent hover:bg-surface-800/50"
                }`}
              >
                <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${tone.dot} ${stage.state === "running" ? "animate-pulse" : ""}`} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm text-surface-100">
                    {stage.title}
                  </span>
                  <span className={`block text-[10px] uppercase tracking-[0.1em] ${tone.text}`}>
                    {tone.label}
                    {stage.state === "running" ? ` · ${stage.progress}%` : ""}
                  </span>
                </span>
              </button>
              {i < stages.length - 1 && (
                <div className="ml-[15px] h-3 w-px bg-surface-700" aria-hidden />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

// ---- center · current-object preview + structured status -------------------

function MetricGrid({ stage }: { stage: WorkflowStage }) {
  if (stage.metrics.length === 0) return null;
  return (
    <dl className="grid grid-cols-2 gap-2 sm:grid-cols-3">
      {stage.metrics.map((m) => (
        <div
          key={m.label}
          className="rounded-sm border border-surface-800 bg-surface-900/40 px-2.5 py-2"
        >
          <dt className="text-[10px] uppercase tracking-[0.1em] text-surface-400">
            {m.label}
          </dt>
          <dd className={`mt-0.5 text-sm font-semibold ${m.verdict ? VERDICT_TEXT[m.verdict] : "text-surface-100"}`}>
            {m.value}
            {m.unit ? <span className="ml-0.5 text-[11px] font-normal text-surface-400">{m.unit}</span> : null}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function StagePreview({ stage }: { stage: WorkflowStage }) {
  const tone = STATE_TONE[stage.state];
  return (
    <section className="flex flex-col gap-4 rounded-md border border-surface-800 bg-surface-900/40 p-4">
      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-surface-400">
            Current object
          </p>
          <h2 className="mt-0.5 truncate text-lg font-semibold text-surface-100">
            {stage.title}
          </h2>
          {stage.currentObject && (
            <p className="mt-0.5 text-sm text-surface-300">{stage.currentObject}</p>
          )}
        </div>
        <StageStatusBadge state={stage.state} />
      </header>

      {stage.state === "running" && (
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-800">
          <div
            className="h-full rounded-full bg-sky-400 transition-all"
            style={{ width: `${stage.progress}%` }}
            role="progressbar"
            aria-valuenow={stage.progress}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>
      )}

      {/* Honest-preview placeholder: the real viewport (geometry/mesh/field)
          mounts here when wired. For the design preview we show the structured
          state, which is the substance the operator actually reasons over. */}
      <div className={`rounded-sm border border-dashed ${tone.ring} bg-surface-950/40 px-3 py-6 text-center`}>
        <p className="text-[11px] uppercase tracking-[0.12em] text-surface-400">
          {stage.title} preview
        </p>
        <p className="mt-1 text-xs text-surface-500">
          3D viewport / chart mounts here when wired to the backend.
        </p>
      </div>

      <MetricGrid stage={stage} />

      {stage.advisor && (
        <p className="rounded-sm border-l-2 border-surface-600 bg-surface-900/60 px-3 py-2 text-sm leading-relaxed text-surface-200">
          {stage.advisor}
        </p>
      )}

      {stage.warnings.map((w) => (
        <p key={w} className="flex gap-2 text-sm text-contract-hazard">
          <span aria-hidden>▲</span>
          <span>{w}</span>
        </p>
      ))}
      {stage.errors.map((e) => (
        <p key={e} className="flex gap-2 text-sm text-contract-fail">
          <span aria-hidden>✕</span>
          <span>{e}</span>
        </p>
      ))}

      {stage.nextAction && (
        <div className="rounded-sm bg-surface-800/60 px-3 py-2">
          <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-surface-400">
            Next action
          </p>
          <p className="mt-0.5 text-sm text-surface-100">{stage.nextAction}</p>
        </div>
      )}

      {stage.artifacts.length > 0 && (
        <div>
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-surface-400">
            Artifacts
          </p>
          <ul className="flex flex-wrap gap-1.5">
            {stage.artifacts.map((a) => (
              <li
                key={a.name}
                className="rounded-sm border border-surface-700 bg-surface-900/60 px-2 py-1 text-[11px] text-surface-200"
              >
                <span className="text-surface-500">{a.kind}</span> · {a.name}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

// ---- right rail · advisor explanation log ----------------------------------

const LOG_TONE: Record<AdvisorLogEntry["level"], string> = {
  info: "text-surface-300 border-surface-700",
  warn: "text-contract-hazard border-contract-hazard/40",
  block: "text-contract-hazard border-contract-hazard/60",
};

export function AdvisorLog({ entries }: { entries: AdvisorLogEntry[] }) {
  return (
    <aside className="flex flex-col rounded-md border border-surface-800 bg-surface-900/40 p-3">
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-surface-400">
        Advisor log
      </p>
      <ol className="flex flex-col gap-2">
        {entries.map((e, i) => (
          <li
            key={`${e.ts}-${i}`}
            className={`border-l-2 pl-2.5 ${LOG_TONE[e.level]}`}
          >
            <div className="flex items-center gap-2">
              <span className="font-mono text-[10px] text-surface-500">{e.ts}</span>
              {e.level !== "info" && (
                <span className="text-[9px] font-semibold uppercase tracking-[0.12em]">
                  {e.level}
                </span>
              )}
            </div>
            <p className="text-xs leading-snug text-surface-200">{e.message}</p>
          </li>
        ))}
      </ol>
    </aside>
  );
}

// ---- bottom · stage timeline -----------------------------------------------

export function StageTimeline({
  timeline,
  currentStage,
}: {
  timeline: TimelineEntry[];
  currentStage: string;
}) {
  return (
    <section className="rounded-md border border-surface-800 bg-surface-900/40 p-3">
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-surface-400">
        Timeline
      </p>
      <ol className="flex items-stretch gap-1 overflow-x-auto">
        {timeline.map((t, i) => {
          const tone = STATE_TONE[t.state];
          const isCurrent = t.stage === currentStage;
          return (
            <li key={t.stage} className="flex min-w-0 flex-1 items-center gap-1">
              <div
                className={`min-w-0 flex-1 rounded-sm border px-2 py-1.5 ${
                  isCurrent ? "border-surface-500 bg-surface-800" : "border-surface-800 bg-surface-900/60"
                }`}
              >
                <div className="flex items-center gap-1.5">
                  <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${tone.dot} ${t.state === "running" ? "animate-pulse" : ""}`} />
                  <span className="truncate text-xs text-surface-100">{t.label}</span>
                </div>
                <span className="mt-0.5 block font-mono text-[10px] text-surface-500">
                  {t.at}
                </span>
              </div>
              {i < timeline.length - 1 && (
                <span className="shrink-0 text-surface-600" aria-hidden>›</span>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
