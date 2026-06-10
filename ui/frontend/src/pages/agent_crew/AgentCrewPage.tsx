// Agent Crew Observatory — /agent-crew
// V93 · DEC-V93-crew-ui
//
// 只读观察页：可视化多 agent 治理回路（Sponsor → Chief → Workers →
// Codex 异源审查 → loop-auditor → Kogami 战略层 → Git 档案）。
// 全真实工件驱动；任何字段解析不到 → 显示 UNPARSED/未记录；绝不编造默认值。

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { agentCrewApi } from "@/api/agentCrew";
import type { CrewArc } from "@/api/agentCrew";
import { ApiError } from "@/api/client";
import { TopologyGraph } from "./components/TopologyGraph";
import { ArcReplay } from "./components/ArcReplay";
import { ArtifactInspector } from "./components/ArtifactInspector";

// Verdict color dot for arc list
function VerdictDot({ verdict }: { verdict: string }) {
  let cls = "bg-surface-500";
  if (verdict === "APPROVE") cls = "bg-v4-healthy";
  else if (verdict === "APPROVE_WITH_COMMENTS") cls = "bg-yellow-400";
  else if (verdict === "CHANGES_REQUIRED") cls = "bg-v4-active";
  // UNPARSED / MISSING → gray (default)
  return (
    <span
      className={`inline-block h-2 w-2 shrink-0 rounded-full ${cls}`}
      title={verdict}
    />
  );
}

function ArcListRow({
  arc,
  selected,
  onClick,
}: {
  arc: CrewArc;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "flex w-full flex-col gap-1 rounded-sm border px-2 py-1.5 text-left transition-colors",
        selected
          ? "border-v4-borderActive bg-v4-surfaceRaised"
          : "border-transparent hover:border-v4-border hover:bg-v4-surface/60",
      ].join(" ")}
    >
      <div className="flex items-center gap-1.5">
        <span className="font-mono text-[10px] font-semibold text-v4-textSecondary">
          {arc.decision_id}
        </span>
        <span className="text-[10px] text-v4-textTertiary">{arc.date}</span>
        {arc.autonomous && (
          <span className="ml-auto rounded-sm bg-surface-800 px-1 py-0.5 text-[9px] text-surface-300">
            auto
          </span>
        )}
      </div>
      <p className="truncate text-[11px] text-v4-textPrimary">{arc.title}</p>
      {/* Round verdict badges */}
      {arc.codex_rounds.length > 0 && (
        <div className="flex items-center gap-1">
          {arc.codex_rounds.map((r) => (
            <VerdictDot key={r.round} verdict={r.verdict} />
          ))}
          <span className="ml-1 text-[9px] text-v4-textTertiary">
            {arc.codex_rounds.length} round
            {arc.codex_rounds.length > 1 ? "s" : ""}
          </span>
        </div>
      )}
    </button>
  );
}

export function AgentCrewPage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["agent-crew"],
    queryFn: agentCrewApi.getCrewSnapshot,
  });

  const [selectedArcId, setSelectedArcId] = useState<string | null>(null);
  const [activeEdgeIds, setActiveEdgeIds] = useState<string[]>([]);

  const selectedArc: CrewArc | null =
    data?.arcs.find((a) => a.decision_id === selectedArcId) ?? null;

  if (isLoading) {
    return (
      <section className="px-8 py-10 text-v4-textSecondary">
        加载中…
      </section>
    );
  }

  if (isError || !data) {
    const msg =
      error instanceof ApiError
        ? `${error.status}: ${error.message}`
        : String(error);
    return (
      <section className="px-8 py-10">
        <div className="rounded-md border border-contract-fail/40 bg-contract-fail/10 px-4 py-3 text-sm text-contract-fail">
          加载失败: {msg}
        </div>
      </section>
    );
  }

  const { roles, edges, arcs, stats } = data;

  return (
    <div className="flex h-full flex-col gap-4 overflow-hidden px-5 py-5">
      {/* Page header */}
      <header className="shrink-0">
        <h1 className="text-lg font-semibold text-v4-textPrimary">
          Agent Crew Observatory · 多 agent 治理回路
        </h1>
        <p className="mt-0.5 text-[11px] text-v4-textTertiary">
          数据全部解析自 .planning/decisions/*.md 和 reports/codex_tool_reports/*
          等真实工件；解析不到的字段显示 UNPARSED / 未记录，绝不编造默认值。
          启发式解析字段（verdict / P1-P3 计数）已标注「启发式解析 · 点击看原文」。
        </p>
        {/* Stats chips */}
        <div className="mt-2 flex flex-wrap gap-2">
          {[
            { label: "决策文件", value: stats.decisions_total },
            { label: "Codex 报告", value: stats.codex_reports_total },
            { label: "autonomous", value: stats.autonomous_total },
            { label: "loop-auditor", value: stats.loop_auditor_total },
            { label: "Kogami", value: stats.kogami_total },
          ].map((chip) => (
            <span
              key={chip.label}
              className="rounded-sm border border-v4-border bg-v4-surfaceRaised px-2 py-0.5 text-[10px] text-v4-textSecondary"
            >
              {chip.label}{" "}
              <strong className="text-v4-textPrimary">{chip.value}</strong>
            </span>
          ))}
        </div>
      </header>

      {/* Three-column layout */}
      <main className="grid min-h-0 flex-1 grid-cols-1 gap-4 overflow-hidden lg:grid-cols-[340px_minmax(0,1fr)_360px]">
        {/* Left: TopologyGraph */}
        <aside className="overflow-y-auto">
          <TopologyGraph
            roles={roles}
            edges={edges}
            activeEdgeIds={activeEdgeIds}
          />
        </aside>

        {/* Center: Arc list + ArcReplay */}
        <section className="flex min-h-0 flex-col overflow-hidden rounded-md border border-v4-border bg-v4-surface">
          <header className="shrink-0 border-b border-v4-border px-3 py-2">
            <h2 className="text-[10px] font-semibold uppercase tracking-[0.14em] text-v4-textSecondary">
              Arc 列表（{arcs.length} · date ≥ 2026-05-01 或含 loop_auditor/confidence 字段）
            </h2>
          </header>

          {/* Arc list */}
          <div className="flex-1 overflow-y-auto px-2 py-1 space-y-0.5">
            {arcs.length === 0 ? (
              <p className="px-2 py-4 text-[11px] text-v4-textTertiary">
                暂无符合条件的 Arc
              </p>
            ) : (
              arcs.map((arc) => (
                <ArcListRow
                  key={arc.decision_id}
                  arc={arc}
                  selected={arc.decision_id === selectedArcId}
                  onClick={() => setSelectedArcId(arc.decision_id)}
                />
              ))
            )}
          </div>

          {/* ArcReplay */}
          {selectedArc && (
            <div className="shrink-0 border-t border-v4-border px-3 py-2 overflow-y-auto max-h-64">
              <ArcReplay
                arc={selectedArc}
                onActiveEdgesChange={setActiveEdgeIds}
              />
            </div>
          )}
        </section>

        {/* Right: ArtifactInspector */}
        <aside className="overflow-y-auto rounded-md border border-v4-border bg-v4-surface px-3 py-3">
          <h2 className="mb-2 shrink-0 text-[10px] font-semibold uppercase tracking-[0.14em] text-v4-textSecondary">
            工件检查器
          </h2>
          <ArtifactInspector decisionId={selectedArcId} />
        </aside>
      </main>
    </div>
  );
}

export default AgentCrewPage;
