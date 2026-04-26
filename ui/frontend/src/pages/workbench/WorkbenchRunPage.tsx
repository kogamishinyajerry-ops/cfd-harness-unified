import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "@/api/client";
import type { PhaseId, RunPhaseEvent } from "@/types/wizard";

// Stage 8a — wizard run timeline. Subscribes to /api/wizard/run/:id/stream
// SSE and walks 5 phases (geometry → mesh → boundary → solver → compare).
// Each phase has its own log panel, summary line on close, and visual
// state transitions. The visible "story" is the value-add over RunMonitor's
// raw-residual stream.

const PHASE_ORDER: PhaseId[] = [
  "geometry",
  "mesh",
  "boundary",
  "solver",
  "compare",
];
const PHASE_LABEL_ZH: Record<PhaseId, string> = {
  geometry: "几何与边界",
  mesh: "网格生成",
  boundary: "边界条件",
  solver: "求解器迭代",
  compare: "对照黄金标准",
};
const PHASE_GLYPH: Record<PhaseId, string> = {
  geometry: "▱",
  mesh: "#",
  boundary: "∂",
  solver: "Σ",
  compare: "⚖",
};

interface PhaseState {
  status: "pending" | "running" | "ok" | "fail";
  message?: string;
  summary?: string;
  logs: string[];
  metrics: { key: string; value: number; t: number }[];
}

const INITIAL: PhaseState = {
  status: "pending",
  logs: [],
  metrics: [],
};

// Auto-jump grace window after run_done before navigating to the run-detail
// page. Long enough that the user notices the run has completed and reads
// the final phase summary; short enough that they don't have to wait
// awkwardly. Skipped if the user clicks the manual jump button.
const AUTO_JUMP_DELAY_MS = 3500;

export function WorkbenchRunPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const [phases, setPhases] = useState<Record<PhaseId, PhaseState>>(() =>
    Object.fromEntries(PHASE_ORDER.map((p) => [p, { ...INITIAL }])) as Record<
      PhaseId,
      PhaseState
    >,
  );
  const [overall, setOverall] = useState<"running" | "done">("running");
  const [overallSummary, setOverallSummary] = useState<string>("");
  // M3: capture run_id from any incoming RealSolverDriver event so we can
  // auto-redirect on run_done. Stays null when MockSolverDriver is on
  // (mock omits run_id) — the auto-jump logic below short-circuits in that
  // case and the page just shows the completion banner.
  const [runId, setRunId] = useState<string | null>(null);
  const sourceRef = useRef<EventSource | null>(null);
  const jumpTimerRef = useRef<number | null>(null);

  useEffect(() => {
    if (!caseId) return;
    const url = api.wizardRunStreamUrl(caseId);
    const es = new EventSource(url);
    sourceRef.current = es;
    es.onmessage = (msg) => {
      try {
        const ev: RunPhaseEvent = JSON.parse(msg.data);
        applyEvent(ev);
      } catch {
        // ignore malformed lines (mock backend emits clean JSON; future
        // real backend would buffer partial lines, but EventSource
        // already framing-checks "data:" boundaries)
      }
    };
    es.onerror = () => {
      es.close();
    };
    return () => {
      es.close();
      sourceRef.current = null;
      if (jumpTimerRef.current !== null) {
        window.clearTimeout(jumpTimerRef.current);
        jumpTimerRef.current = null;
      }
    };
  }, [caseId]);

  // M3: schedule the auto-jump after run_done lands. Effect runs whenever
  // overall flips to "done" — at that point runId is already populated by
  // the SSE stream (RealSolverDriver attaches run_id to every event).
  useEffect(() => {
    if (overall !== "done" || !runId || !caseId) return;
    jumpTimerRef.current = window.setTimeout(() => {
      navigate(
        `/workbench/case/${encodeURIComponent(caseId)}/run/${encodeURIComponent(runId)}`,
      );
    }, AUTO_JUMP_DELAY_MS);
    return () => {
      if (jumpTimerRef.current !== null) {
        window.clearTimeout(jumpTimerRef.current);
        jumpTimerRef.current = null;
      }
    };
  }, [overall, runId, caseId, navigate]);

  function applyEvent(ev: RunPhaseEvent) {
    // M3: capture run_id off any event (RealSolverDriver attaches it
    // unconditionally). MockSolverDriver leaves it undefined — runId
    // stays null and auto-jump never fires.
    if (ev.run_id && !runId) {
      setRunId(ev.run_id);
    }
    if (ev.type === "phase_start" && ev.phase) {
      setPhases((prev) => ({
        ...prev,
        [ev.phase!]: {
          ...prev[ev.phase!],
          status: "running",
          message: ev.message ?? prev[ev.phase!].message,
        },
      }));
    } else if (ev.type === "log" && ev.phase && ev.line) {
      setPhases((prev) => ({
        ...prev,
        [ev.phase!]: {
          ...prev[ev.phase!],
          logs: [...prev[ev.phase!].logs, ev.line!],
        },
      }));
    } else if (ev.type === "metric" && ev.phase && ev.metric_key) {
      setPhases((prev) => ({
        ...prev,
        [ev.phase!]: {
          ...prev[ev.phase!],
          metrics: [
            ...prev[ev.phase!].metrics,
            { key: ev.metric_key!, value: ev.metric_value ?? 0, t: ev.t },
          ],
        },
      }));
    } else if (ev.type === "phase_done" && ev.phase) {
      setPhases((prev) => ({
        ...prev,
        [ev.phase!]: {
          ...prev[ev.phase!],
          status: ev.status === "fail" ? "fail" : "ok",
          summary: ev.summary ?? prev[ev.phase!].summary,
        },
      }));
    } else if (ev.type === "run_done") {
      setOverall("done");
      setOverallSummary(ev.summary ?? "run complete");
    }
  }

  if (!caseId) {
    return (
      <section className="px-8 py-10 text-sm text-contract-fail">
        Missing case_id in URL.
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-5xl px-8 py-8">
      <header className="mb-6">
        <p className="mono text-[11px] uppercase tracking-wider text-surface-500">
          workbench · run
        </p>
        <h1 className="mt-1 text-2xl font-semibold text-surface-100">{caseId}</h1>
        <p className="mt-1 text-sm text-surface-400">
          {overall === "running"
            ? runId
              ? "RealSolverDriver 执行中（Docker + OpenFOAM）"
              : "5 阶段流水线执行中（mock solver · Stage 8a）"
            : "运行已完成"}
        </p>
        <p className="mt-1 text-[11px] text-surface-500">
          {overallSummary || "等待事件流..."}
        </p>
        {runId && (
          <p className="mt-2 font-mono text-[10px] text-surface-500">
            run_id = {runId}
          </p>
        )}
      </header>

      {overall === "done" && runId && (
        <div className="mb-4 flex items-center justify-between rounded-md border border-emerald-700/40 bg-emerald-700/10 px-4 py-2 text-[12px] text-emerald-300">
          <span>
            自动跳转至结果页 (run detail) · 3.5s 后,{" "}
            <span className="font-mono text-[10px] text-surface-400">{runId}</span>
          </span>
          <Link
            to={`/workbench/case/${encodeURIComponent(caseId)}/run/${encodeURIComponent(runId)}`}
            className="rounded-sm bg-emerald-700/40 px-3 py-1 text-emerald-200 hover:bg-emerald-700/60"
          >
            立即跳转 →
          </Link>
        </div>
      )}

      <Stepper phases={phases} />

      <div className="mt-6 space-y-3">
        {PHASE_ORDER.map((p) => (
          <PhasePanel key={p} phase={p} state={phases[p]} />
        ))}
      </div>

      {overall === "done" && (
        <div className="mt-8 rounded-md border border-surface-800 bg-surface-900/40 p-4">
          <h3 className="mb-2 text-sm font-semibold text-surface-200">下一步</h3>
          <ul className="space-y-1.5 text-sm text-surface-300">
            <li>
              ·{" "}
              <Link
                to={`/cases/${encodeURIComponent(caseId)}/edit`}
                className="text-surface-100 underline-offset-2 hover:underline"
              >
                打开 YAML 编辑器
              </Link>{" "}
              微调参数 / 添加 gold_standard 块
            </li>
            <li>
              ·{" "}
              <Link
                to="/workbench/new"
                className="text-surface-100 underline-offset-2 hover:underline"
              >
                再建一个新案例
              </Link>{" "}
              对比不同模板 / 不同 Re
            </li>
            <li className="text-[11px] text-surface-500">
              · Stage 8b 落地真实 OpenFOAM 调度后，本页会切换到{" "}
              <span className="mono">simpleFoam</span> /{" "}
              <span className="mono">icoFoam</span> 实际 stdout 流，
              metrics 区会出真实残差曲线。
            </li>
          </ul>
        </div>
      )}
    </section>
  );
}

function Stepper({ phases }: { phases: Record<PhaseId, PhaseState> }) {
  return (
    <nav className="grid grid-cols-5 gap-1">
      {PHASE_ORDER.map((p) => {
        const s = phases[p];
        const cls =
          s.status === "ok"
            ? "border-contract-pass/40 bg-contract-pass/10 text-contract-pass"
            : s.status === "fail"
              ? "border-contract-fail/40 bg-contract-fail/10 text-contract-fail"
              : s.status === "running"
                ? "border-surface-300 bg-surface-100/5 text-surface-100"
                : "border-surface-800 bg-surface-900/40 text-surface-500";
        return (
          <div
            key={p}
            className={`rounded-sm border px-3 py-2 text-[11px] transition ${cls}`}
          >
            <div className="mono mb-0.5 flex items-center justify-between">
              <span className="font-medium">{PHASE_GLYPH[p]} {p}</span>
              <span>{s.status === "running" ? "···" : s.status === "ok" ? "✓" : s.status === "fail" ? "✕" : "—"}</span>
            </div>
            <div className="text-surface-300">{PHASE_LABEL_ZH[p]}</div>
          </div>
        );
      })}
    </nav>
  );
}

function PhasePanel({ phase, state }: { phase: PhaseId; state: PhaseState }) {
  const isActive = state.status === "running";
  const isDone = state.status === "ok";
  const isFail = state.status === "fail";
  const isPending = state.status === "pending";

  return (
    <details
      open={isActive || isFail}
      className={`group rounded-md border ${
        isFail
          ? "border-contract-fail/40 bg-contract-fail/5"
          : isDone
            ? "border-contract-pass/30 bg-contract-pass/5"
            : isActive
              ? "border-surface-300 bg-surface-100/5"
              : "border-surface-800 bg-surface-900/40"
      }`}
    >
      <summary className="cursor-pointer select-none px-4 py-3">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-semibold text-surface-100">
              <span className="mono mr-2 text-[11px] text-surface-500">
                {PHASE_GLYPH[phase]}
              </span>
              {PHASE_LABEL_ZH[phase]}
            </div>
            {state.message && (
              <div className="mt-0.5 text-[11px] text-surface-500">
                {state.message}
              </div>
            )}
            {state.summary && (
              <div className="mono mt-1 text-[11px] text-surface-300">
                → {state.summary}
              </div>
            )}
          </div>
          <span
            className={`mono text-[10px] uppercase tracking-wider ${
              isFail
                ? "text-contract-fail"
                : isDone
                  ? "text-contract-pass"
                  : isActive
                    ? "text-surface-200"
                    : "text-surface-500"
            }`}
          >
            {isPending && "待执行"}
            {isActive && "执行中"}
            {isDone && "完成"}
            {isFail && "失败"}
          </span>
        </div>
      </summary>
      {(state.logs.length > 0 || state.metrics.length > 0) && (
        <div className="border-t border-surface-800 bg-surface-950/40 px-4 py-3">
          {state.logs.length > 0 && (
            <pre className="mono max-h-40 overflow-auto whitespace-pre-wrap text-[11px] leading-relaxed text-surface-300">
              {state.logs.join("\n")}
            </pre>
          )}
          {state.metrics.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5 text-[11px]">
              {state.metrics.map((m, i) => (
                <span
                  key={i}
                  className="mono rounded-sm border border-surface-800 bg-surface-900 px-1.5 py-0.5 text-surface-400"
                >
                  {m.key}={m.value.toExponential(2)}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </details>
  );
}
