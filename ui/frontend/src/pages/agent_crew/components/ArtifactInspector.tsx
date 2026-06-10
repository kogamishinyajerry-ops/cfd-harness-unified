// ArtifactInspector — shows frontmatter + Codex report excerpts for the
// selected arc. V93 · Agent Crew Observatory

import { useQuery } from "@tanstack/react-query";
import { agentCrewApi } from "@/api/agentCrew";
import { ApiError } from "@/api/client";
import { verdictColor } from "./ArcReplay";

interface ArtifactInspectorProps {
  decisionId: string | null;
}

export function ArtifactInspector({ decisionId }: ArtifactInspectorProps) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["arc-detail", decisionId],
    queryFn: () => agentCrewApi.getArcDetail(decisionId!),
    enabled: decisionId != null,
  });

  if (!decisionId) {
    return (
      <div className="flex h-full flex-col items-center justify-center text-[11px] text-v4-textTertiary">
        <span>← 从中栏选择一个 Arc</span>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center text-[11px] text-v4-textSecondary">
        加载中…
      </div>
    );
  }

  if (isError || !data) {
    const msg =
      error instanceof ApiError
        ? `${error.status}: ${error.message}`
        : String(error);
    return (
      <div className="rounded-md border border-contract-fail/40 bg-contract-fail/10 px-3 py-2 text-xs text-contract-fail">
        加载失败: {msg}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 overflow-y-auto text-[11px]">
      <div>
        <h3 className="mb-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-v4-textSecondary">
          Frontmatter
        </h3>
        <div className="overflow-auto rounded-sm border border-v4-border bg-v4-surface p-2">
          <table className="w-full text-[10px]">
            <tbody>
              {Object.entries(data.frontmatter).map(([k, v]) => (
                <tr key={k} className="border-b border-v4-border/50 last:border-0">
                  <td className="py-0.5 pr-2 font-mono text-v4-textSecondary">{k}</td>
                  <td className="py-0.5 font-mono text-v4-textPrimary break-all">{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {data.reports.length > 0 && (
        <div>
          <h3 className="mb-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-v4-textSecondary">
            Codex 报告
          </h3>
          <div className="space-y-3">
            {data.reports.map((report) => (
              <div
                key={`${report.round}-${report.path}`}
                className="rounded-sm border border-v4-border bg-v4-surface"
              >
                <div className="flex items-center gap-2 border-b border-v4-border px-2 py-1">
                  <span className="text-[9px] font-mono text-v4-textTertiary">
                    R{report.round}
                  </span>
                  <span
                    className={[
                      "rounded-sm border px-1 py-0.5 text-[9px]",
                      verdictColor(report.verdict),
                    ].join(" ")}
                  >
                    {report.verdict}
                  </span>
                  <span className="ml-auto truncate text-[9px] text-v4-textTertiary" title={report.path}>
                    {report.path.replace("reports/codex_tool_reports/", "")}
                  </span>
                  <span className="shrink-0 text-[9px] italic text-v4-textTertiary">
                    启发式解析 · 点击看原文
                  </span>
                </div>
                {report.missing ? (
                  <p className="px-2 py-2 text-[10px] text-v4-textTertiary">
                    报告文件缺失（frontmatter 引用了但文件不在仓库）
                  </p>
                ) : (
                  <pre className="max-h-48 overflow-y-auto px-2 py-2 font-mono text-[9px] leading-relaxed text-v4-textSecondary whitespace-pre-wrap break-words">
                    {data.body_excerpt
                      ? `── 正文摘录（前 120 行）──\n${data.body_excerpt}\n\n`
                      : ""}
                    {`── 报告原文 ──\n${report.excerpt}`}
                  </pre>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {data.reports.length === 0 && (
        <div className="text-[10px] text-v4-textTertiary">此 Arc 暂无 Codex 报告</div>
      )}
    </div>
  );
}
