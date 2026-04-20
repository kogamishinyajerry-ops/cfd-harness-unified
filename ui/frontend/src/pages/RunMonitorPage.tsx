import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api, ApiError } from "@/api/client";
import { ResidualChart, type ResidualSample } from "@/components/ResidualChart";
import type { RunStreamEvent } from "@/types/decisions";

// Phase 3 — Run Monitor. Streams synthetic residuals via SSE from
// /api/runs/{case_id}/stream. Checkpoints table reads the snapshot
// endpoint. A real solver-wiring handshake lands in Phase 3.5.

function PhaseBadge({ phase }: { phase: string }) {
  const palette: Record<string, string> = {
    idle: "bg-surface-800 text-surface-300",
    init: "bg-surface-800 text-surface-100",
    linear_solver: "bg-contract-hazard/20 text-contract-hazard",
    checkpoint: "bg-contract-pass/20 text-contract-pass",
    done: "bg-contract-pass text-surface-950",
  };
  return (
    <span className={`rounded-sm px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider ${palette[phase] ?? "bg-surface-800 text-surface-300"}`}>
      {phase}
    </span>
  );
}

export function RunMonitorPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const casesQuery = useQuery({ queryKey: ["cases"], queryFn: api.listCases });

  // When no caseId: show a picker.
  if (!caseId) {
    if (casesQuery.isLoading) {
      return <section className="px-8 py-10 text-surface-300">Loading cases…</section>;
    }
    if (casesQuery.isError || !casesQuery.data) {
      const msg = casesQuery.error instanceof ApiError
        ? `${casesQuery.error.status}: ${casesQuery.error.message}`
        : String(casesQuery.error);
      return (
        <section className="px-8 py-10 text-sm text-contract-fail">Failed to load cases: {msg}</section>
      );
    }
    return (
      <section className="p-8">
        <h1 className="mb-2 text-2xl font-semibold text-surface-100">Run Monitor</h1>
        <p className="mb-6 text-sm text-surface-400">
          Pick a case to start a mock run. Phase 3 streams synthetic residuals only;
          real solver-wiring lands in Phase 3.5.
        </p>
        <ul className="grid gap-2 max-w-2xl">
          {casesQuery.data.map((c) => (
            <li key={c.case_id}>
              <button
                type="button"
                onClick={() => navigate(`/runs/${c.case_id}`)}
                className="w-full rounded-md border border-surface-800 bg-surface-900/40 px-4 py-3 text-left text-sm transition hover:border-surface-700 hover:bg-surface-800/40"
              >
                <strong className="text-surface-100">{c.name}</strong>
                <span className="ml-2 text-[11px] text-surface-500">{c.flow_type} · {c.turbulence_model}</span>
              </button>
            </li>
          ))}
        </ul>
      </section>
    );
  }

  return <RunMonitorInner caseId={caseId} />;
}

function RunMonitorInner({ caseId }: { caseId: string }) {
  const [samples, setSamples] = useState<ResidualSample[]>([]);
  const [phase, setPhase] = useState<string>("idle");
  const [streaming, setStreaming] = useState<boolean>(false);
  const [message, setMessage] = useState<string>("");
  const [checkpointEvents, setCheckpointEvents] = useState<RunStreamEvent[]>([]);
  const sourceRef = useRef<EventSource | null>(null);

  const checkpointsQuery = useQuery({
    queryKey: ["runCheckpoints", caseId],
    queryFn: () => api.getRunCheckpoints(caseId),
  });

  const stop = useCallback(() => {
    if (sourceRef.current) {
      sourceRef.current.close();
      sourceRef.current = null;
    }
    setStreaming(false);
  }, []);

  const start = useCallback(() => {
    stop();
    setSamples([]);
    setCheckpointEvents([]);
    setPhase("init");
    setMessage("Opening stream…");
    setStreaming(true);
    const es = new EventSource(api.runStreamUrl(caseId));
    sourceRef.current = es;
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data) as RunStreamEvent;
        setPhase(data.phase);
        setMessage(data.message);
        if (data.residuals) {
          setSamples((prev) => [
            ...prev,
            { iter: data.iter, Ux: data.residuals!.Ux, Uy: data.residuals!.Uy, p: data.residuals!.p },
          ]);
        }
        if (data.phase === "checkpoint") {
          setCheckpointEvents((prev) => [...prev, data]);
        }
        if (data.phase === "done") {
          setStreaming(false);
          es.close();
          sourceRef.current = null;
        }
      } catch (exc) {
        // Silently ignore malformed events; Phase 3 keeps the UI resilient.
        console.warn("SSE parse error", exc);
      }
    };
    es.onerror = () => {
      setPhase("error");
      setMessage("stream interrupted");
      setStreaming(false);
      es.close();
      sourceRef.current = null;
    };
  }, [caseId, stop]);

  useEffect(() => {
    return () => stop();
  }, [stop]);

  const latestIter = samples[samples.length - 1]?.iter ?? 0;
  const pinnedCheckpoints = useMemo(
    () => checkpointEvents.slice(-8).reverse(),
    [checkpointEvents],
  );

  return (
    <section className="p-8">
      <header className="mb-4 flex items-baseline justify-between">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-surface-500">
            <Link to="/runs" className="hover:text-surface-300">Runs</Link>
            <span className="mx-1.5">/</span>
            <span>{caseId}</span>
          </div>
          <h1 className="mt-1 text-2xl font-semibold text-surface-100">Run Monitor · {caseId}</h1>
          <p className="mt-1 text-[12px] text-surface-400">
            Synthetic residual stream · Phase 3 · real solver wiring in Phase 3.5.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <PhaseBadge phase={phase} />
          {!streaming ? (
            <button
              type="button"
              onClick={start}
              className="rounded-sm bg-contract-pass/80 px-4 py-1.5 text-sm font-medium text-surface-950 transition hover:bg-contract-pass"
            >
              Start mock run
            </button>
          ) : (
            <button
              type="button"
              onClick={stop}
              className="rounded-sm bg-contract-fail/80 px-4 py-1.5 text-sm font-medium text-surface-100 transition hover:bg-contract-fail"
            >
              Stop
            </button>
          )}
        </div>
      </header>

      <div className="grid grid-cols-[1fr_320px] gap-4">
        <div className="space-y-3">
          <ResidualChart samples={samples} />
          <div className="rounded-md border border-surface-800 bg-surface-900/40 p-3 text-[12px]">
            <h3 className="mb-1 text-[11px] uppercase tracking-wider text-surface-400">Solver status</h3>
            <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 font-mono text-surface-200">
              <dt className="text-surface-500">iter</dt><dd>{latestIter}</dd>
              <dt className="text-surface-500">phase</dt><dd>{phase}</dd>
              <dt className="text-surface-500">samples</dt><dd>{samples.length}</dd>
              <dt className="text-surface-500">last</dt><dd className="truncate">{message}</dd>
            </dl>
          </div>
        </div>

        <div className="space-y-3">
          <div className="rounded-md border border-surface-800 bg-surface-900/40 p-3">
            <h3 className="mb-1 text-[11px] uppercase tracking-wider text-surface-400">Live checkpoints</h3>
            {pinnedCheckpoints.length === 0 ? (
              <p className="text-xs text-surface-500">— none yet —</p>
            ) : (
              <ul className="space-y-1 text-[12px]">
                {pinnedCheckpoints.map((cp, i) => (
                  <li key={i} className="font-mono text-surface-200">
                    iter <strong>{cp.iter}</strong> · t={cp.t_sec}s · phase <PhaseBadge phase={cp.phase} />
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="rounded-md border border-surface-800 bg-surface-900/40 p-3">
            <h3 className="mb-1 text-[11px] uppercase tracking-wider text-surface-400">Pinned snapshot</h3>
            {checkpointsQuery.isLoading && (
              <p className="text-xs text-surface-500">loading…</p>
            )}
            {checkpointsQuery.data && (
              <ul className="space-y-1 font-mono text-[11px]">
                {checkpointsQuery.data.checkpoints.map((cp) => (
                  <li key={cp.iter} className="flex justify-between text-surface-300">
                    <span>iter {cp.iter}</span>
                    <span>{cp.residual_Ux.toExponential(1)}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="flex gap-2">
            <Link
              to={`/cases/${caseId}/report`}
              className="flex-1 rounded-sm border border-surface-700 bg-surface-800/40 px-3 py-1.5 text-center text-xs text-surface-300 transition hover:bg-surface-800"
            >
              View report →
            </Link>
            <Link
              to={`/cases/${caseId}/edit`}
              className="flex-1 rounded-sm border border-surface-700 bg-surface-800/40 px-3 py-1.5 text-center text-xs text-surface-300 transition hover:bg-surface-800"
            >
              Edit case →
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
