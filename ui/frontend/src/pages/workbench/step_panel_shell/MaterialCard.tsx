/**
 * V68-C.1 · MaterialCard · read-only display of a case's committed
 * physics state (material + regime).
 *
 * Two render modes driven by usePhysicsState:
 *   - committed: case is in IMPORTED_DIR with both dicts on disk;
 *     parsed fields + raw dict text visible (raw under <details>).
 *   - reference: case is whitelist-only (not materialized in
 *     IMPORTED_DIR); parsed fields derived from CaseDetail
 *     (solver / turbulence_model / Re), and the "raw dict" pane shows
 *     "(whitelist case · not materialized — reference metadata only)".
 *
 * V130 invariant: this card is advisory display only. It never writes,
 * never POSTs, never auto-fires. Engineer reads → decides.
 */
import { usePhysicsState, type PhysicsView } from "./usePhysicsState";

interface MaterialCardProps {
  caseId: string | null | undefined;
}

export function MaterialCard({ caseId }: MaterialCardProps) {
  const view = usePhysicsState(caseId);
  return (
    <section
      data-testid="material-card"
      data-status={view.status}
      className="rounded-sm border border-surface-700 bg-surface-900/50 p-3"
    >
      <header className="flex items-baseline justify-between gap-2">
        <h2 className="text-sm font-medium text-surface-100">
          Material &amp; Regime
        </h2>
        <StatusBadge view={view} />
      </header>
      <p className="mt-0.5 text-[11px] text-surface-500">
        Read-only view of <code>constant/physicalProperties</code> +{" "}
        <code>constant/momentumTransport</code>. Engineer applies via
        PhysicsPanel below; AI never auto-writes (V130).
      </p>

      <CardBody view={view} />
    </section>
  );
}

function StatusBadge({ view }: { view: PhysicsView }) {
  if (view.status === "committed") {
    return (
      <span
        data-testid="material-card-badge"
        className="rounded-sm border border-emerald-500/40 bg-emerald-500/10 px-1.5 py-0.5 font-mono text-[10px] text-emerald-200"
      >
        committed
      </span>
    );
  }
  if (view.status === "reference") {
    return (
      <span
        data-testid="material-card-badge"
        className="rounded-sm border border-sky-500/40 bg-sky-500/10 px-1.5 py-0.5 font-mono text-[10px] text-sky-200"
      >
        reference (whitelist)
      </span>
    );
  }
  if (view.status === "error") {
    return (
      <span
        data-testid="material-card-badge"
        className="rounded-sm border border-rose-500/40 bg-rose-500/10 px-1.5 py-0.5 font-mono text-[10px] text-rose-200"
      >
        error
      </span>
    );
  }
  if (view.status === "loading") {
    return (
      <span
        data-testid="material-card-badge"
        className="rounded-sm border border-surface-700 bg-surface-800/40 px-1.5 py-0.5 font-mono text-[10px] text-surface-400"
      >
        loading…
      </span>
    );
  }
  return null;
}

function CardBody({ view }: { view: PhysicsView }) {
  if (view.status === "no-case") {
    return (
      <p
        data-testid="material-card-no-case"
        className="mt-2 text-[11px] text-surface-500"
      >
        Open a case to see its physics state.
      </p>
    );
  }
  if (view.status === "loading") {
    return (
      <p
        data-testid="material-card-loading"
        className="mt-2 font-mono text-[11px] text-surface-400"
      >
        Loading physics state…
      </p>
    );
  }
  if (view.status === "error") {
    return (
      <p
        data-testid="material-card-error"
        className="mt-2 rounded-sm border border-rose-700/40 bg-rose-900/10 px-2 py-1 font-mono text-[11px] text-rose-200"
      >
        {view.message}
      </p>
    );
  }

  const parsed = view.parsed;

  return (
    <div className="mt-3 space-y-2">
      <div
        data-testid="material-card-readout"
        className="space-y-0.5 rounded-sm border border-surface-800 bg-surface-950/50 p-2 font-mono text-[11px] text-surface-400"
      >
        <Row label="solver" value={parsed.solver ?? "—"} />
        <Row
          label="transport"
          value={parsed.transportModel ?? "—"}
          testId="material-card-transport-model"
        />
        <Row
          label="ν"
          value={parsed.nu !== null ? `${parsed.nu.toExponential(3)} m²/s` : "—"}
          testId="material-card-nu"
        />
        <Row
          label="ρ"
          value={parsed.rho !== null ? `${parsed.rho.toFixed(2)} kg/m³` : "—"}
          testId="material-card-rho"
        />
        <Row
          label="regime"
          value={parsed.simulationType ?? "—"}
          testId="material-card-regime"
        />
        {parsed.rasModel && (
          <Row label="RAS" value={parsed.rasModel} />
        )}
        {parsed.turbulenceModel && parsed.turbulenceModel !== parsed.simulationType && (
          <Row label="turbulence" value={parsed.turbulenceModel} />
        )}
        {parsed.reynolds !== null && (
          <Row
            label="Re"
            value={parsed.reynolds.toExponential(2)}
            testId="material-card-reynolds"
          />
        )}
      </div>

      <details
        data-testid="material-card-raw"
        className="rounded-sm border border-slate-700/40 bg-slate-900/30"
      >
        <summary className="cursor-pointer px-2 py-1 text-[11px] uppercase tracking-wider text-slate-300 hover:text-slate-100">
          Raw dict text
        </summary>
        <RawDictPane view={view} />
      </details>
    </div>
  );
}

function RawDictPane({
  view,
}: {
  view: Extract<PhysicsView, { status: "committed" | "reference" }>;
}) {
  if (view.status === "reference") {
    return (
      <p
        data-testid="material-card-raw-reference"
        className="px-2 py-2 font-mono text-[11px] text-slate-400"
      >
        (whitelist case · not materialized — reference metadata only)
      </p>
    );
  }
  return (
    <div className="space-y-2 px-2 py-2">
      <RawSection
        label="constant/physicalProperties"
        text={view.materialDictText}
        testId="material-card-raw-material"
      />
      <RawSection
        label="constant/momentumTransport"
        text={view.regimeDictText}
        testId="material-card-raw-regime"
      />
    </div>
  );
}

function RawSection({
  label,
  text,
  testId,
}: {
  label: string;
  text: string | null;
  testId: string;
}) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-slate-500">
        {label}
      </div>
      <pre
        data-testid={testId}
        className="mt-1 max-h-48 overflow-auto rounded-sm border border-slate-800 bg-slate-950/70 p-2 font-mono text-[10px] text-slate-300"
      >
        {text ?? "(not committed yet)"}
      </pre>
    </div>
  );
}

function Row({
  label,
  value,
  testId,
}: {
  label: string;
  value: string;
  testId?: string;
}) {
  return (
    <div className="flex gap-2" data-testid={testId}>
      <span className="text-surface-500">{label}:</span>
      <span className="text-surface-200">{value}</span>
    </div>
  );
}
