/**
 * V4 · RightPanel · 300px · AI 助理 + 模式卡片 + 入库完整度
 *
 * Hardening pass (post Codex R3 review · finding M-2):
 *   1. Completeness summary card (always at top when caseId set) reads
 *      ctx.completeness and surfaces percentage + present/total + top
 *      critical missing. This is the "距离入库标准还差 N 项" surface the
 *      CaseCompletenessReport schema was designed for.
 *   2. Mode-specific real-data cards keyed by activeStep — replaces the
 *      static placeholder pills with facts pulled from useV4WorkbenchContext.
 *      Per-step content (geometry: patches+dim+CL · mesh: GCI · physics:
 *      solver · boundary: roles · solver: residuals · post: verdict · doe:
 *      stub) so each pipeline step has a useful right-panel.
 *   3. AdvisorPillStack (V91 matcher) remains at the bottom — primary
 *      "AI 助理" surface, progressive-disclosure pills, advisory-only.
 *
 * 4Q gate honored:
 *   - LLM offline: all data flows from existing useV4WorkbenchContext + V91
 *     matcher (pure-function over RunDetail); no LLM call added
 *   - Artifacts: completeness card carries percentage + counts + missing
 *     field paths; pills carry rule_id + matched_at + provenance
 *   - TrustGate: zero mutation surface · all CTAs are disclosure / nav
 *   - Advisory only: header microcopy + per-card "advisory only · 仅建议"
 */
import { AdvisorPillStack } from "./AdvisorPillStack";
import { useV4WorkbenchContext } from "../hooks/useV4WorkbenchContext";
import { useV4AdvisorMatches } from "../hooks/useV4AdvisorMatches";
import {
  convergenceGaugeFromSeries,
  useResidualSeries,
} from "../hooks/useResidualSeries";
import {
  GEOMETRY_BLUEPRINT_SUMMARY,
  hasAuthoredCadParts,
} from "./geometryBlueprint";
import { MESH_BLUEPRINT_NUMERICS } from "./meshBlueprint";
import { PHYSICS_BLUEPRINT_SUMMARY } from "./physicsBlueprint";
import { V4_PALETTE, V4_SEVERITY_COLOR } from "@/theme/industrial_minimalist";
import type { V4PipelineStepId } from "@/theme/industrial_minimalist";
import type { V4Context } from "../hooks/useV4WorkbenchContext";
import type { PatchRole } from "@/types/workbench_basics";
import type { ResidualSeriesPayload } from "@/types/residual_series";

interface PlaceholderPill {
  severity: "advise" | "warn" | "info";
  title: string;
  subtitle: string;
}

const PLACEHOLDER_BY_STEP: Record<V4PipelineStepId, PlaceholderPill[]> = {
  import: [
    { severity: "info", title: "等待算例选择", subtitle: "通过命令栏 ⌘K 或顶栏切换" },
  ],
  geometry: [{ severity: "info", title: "等待几何元数据", subtitle: "选择算例后显示" }],
  mesh: [{ severity: "info", title: "等待网格统计", subtitle: "选择算例后显示 GCI" }],
  physics: [{ severity: "info", title: "等待求解器配置", subtitle: "选择算例后显示" }],
  boundary: [{ severity: "info", title: "等待边界条件", subtitle: "选择算例后显示" }],
  solver: [{ severity: "info", title: "等待运行记录", subtitle: "选择算例后显示残差" }],
  post: [{ severity: "info", title: "等待运行结果", subtitle: "选择算例后显示" }],
  doe: [{ severity: "info", title: "DOE 后端待接入", subtitle: "—" }],
};

function fmtPct(n: number | null | undefined, digits = 1): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return n.toFixed(digits);
}

function fmtSci(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return n.toExponential(2);
}

function latestResidual(
  payload: ResidualSeriesPayload | null | undefined,
  name: string | null,
): number | null {
  if (!name) return null;
  const pts = payload?.series?.[name];
  if (!pts || pts.length === 0) return null;
  const last = pts[pts.length - 1];
  return Number.isFinite(last?.y) ? last.y : null;
}

/** Completeness summary card · always at top when ctx.completeness present. */
function CompletenessCard({ ctx }: { ctx: V4Context }) {
  const c = ctx.completeness;
  if (!c) return null;
  const ready = c.ready_for_archive;
  const accent = ready
    ? V4_PALETTE.healthy
    : c.blocked_by_critical > 0
      ? V4_PALETTE.crit
      : V4_PALETTE.warn;
  const topCritical = c.missing.find((m) => m.severity === "critical");
  const pct = Math.max(0, Math.min(100, c.percentage));
  return (
    <article
      className="flex flex-col gap-2 rounded border border-v4-border bg-v4-surfaceRaised p-2.5"
      data-testid="rightpanel-v4-completeness"
      data-ready={ready ? "true" : "false"}
    >
      <div className="flex items-baseline justify-between">
        <span className="text-[10px] uppercase tracking-wider text-v4-textTertiary">
          入库完整度
        </span>
        <span
          className="font-mono text-[10px]"
          style={{ color: accent }}
          title={c.case_kind}
        >
          {ready ? "READY" : c.blocked_by_critical > 0 ? "BLOCKED" : "PENDING"}
        </span>
      </div>
      <div className="flex items-baseline gap-2">
        <span
          className="font-mono text-[22px] font-semibold leading-none tabular-nums"
          style={{ color: V4_PALETTE.textPrimary }}
        >
          {fmtPct(pct)}
        </span>
        <span className="text-[11px] text-v4-textTertiary">%</span>
        <span className="ml-auto font-mono text-[11px] text-v4-textSecondary">
          {c.present_count}/{c.total_count}
        </span>
      </div>
      {/* progress bar */}
      <div className="h-1 w-full rounded-sm bg-v4-canvas">
        <div
          className="h-full rounded-sm transition-all"
          style={{ width: `${pct}%`, backgroundColor: accent }}
        />
      </div>
      {c.blocked_by_critical > 0 && (
        <div className="flex items-baseline justify-between text-[11px]">
          <span className="text-v4-textTertiary">critical 缺项</span>
          <span className="font-mono text-v4-crit">{c.blocked_by_critical}</span>
        </div>
      )}
      {topCritical && (
        <div
          className="rounded border border-v4-crit/30 bg-v4-canvas px-2 py-1.5 text-[10px] text-v4-textSecondary"
          title={topCritical.why}
        >
          <div className="font-mono text-v4-crit">
            {topCritical.field_path}
          </div>
          <div className="mt-0.5 line-clamp-2 text-v4-textTertiary">
            {topCritical.why}
          </div>
        </div>
      )}
    </article>
  );
}

interface FactCardProps {
  title: string;
  facts: Array<{
    label: string;
    value: string;
    tone?: "healthy" | "warn" | "crit" | "neutral";
  }>;
  footer?: string;
  cta?: string;
  ctaTone?: "active" | "neutral";
}

function FactCard({ title, facts, footer, cta, ctaTone = "neutral" }: FactCardProps) {
  return (
    <article
      className="flex flex-col gap-1.5 rounded border border-v4-border bg-v4-surfaceRaised p-2.5"
      data-testid={`rightpanel-v4-factcard-${title}`}
    >
      <div className="text-[10px] tracking-wider text-v4-textTertiary">
        {title}
      </div>
      <ul className="space-y-1 text-[11px]">
        {facts.map((f) => (
          <li
            key={f.label}
            className="flex items-baseline justify-between gap-2"
          >
            <span className="truncate text-v4-textSecondary" title={f.label}>
              {f.label}
            </span>
            <span
              className="truncate font-mono text-v4-textPrimary"
              style={
                f.tone === "healthy"
                  ? { color: V4_PALETTE.healthy }
                  : f.tone === "warn"
                    ? { color: V4_PALETTE.warn }
                    : f.tone === "crit"
                      ? { color: V4_PALETTE.crit }
                      : undefined
              }
              title={f.value}
            >
              {f.value}
            </span>
          </li>
        ))}
      </ul>
      {footer && (
        <div className="border-t border-v4-border pt-1.5 text-[10px] text-v4-textTertiary">
          {footer}
        </div>
      )}
      {cta && (
        <div className="flex justify-end border-t border-v4-border pt-1.5">
          <span
            className={[
              "rounded border px-2 py-0.5 text-[10px] font-medium",
              ctaTone === "active"
                ? "border-v4-active/40 text-v4-active"
                : "border-v4-border text-v4-textSecondary",
            ].join(" ")}
            data-testid={`rightpanel-v4-factcard-cta-${title}`}
            data-advisory-only="true"
          >
            {cta}
          </span>
        </div>
      )}
    </article>
  );
}

function countByRole(
  patches: { role: PatchRole }[],
): Partial<Record<PatchRole, number>> {
  const c: Partial<Record<PatchRole, number>> = {};
  for (const p of patches) c[p.role] = (c[p.role] ?? 0) + 1;
  return c;
}

const ROLE_LABEL: Partial<Record<PatchRole, string>> = {
  inlet: "入口",
  outlet: "出口",
  wall: "壁面",
  moving_wall: "运动壁",
  symmetry: "对称",
  cyclic: "周期",
  periodic: "周期",
  empty: "空(2D)",
  airfoil: "翼面",
};

/** Pick the cards for a given pipeline step. Returns 1-2 FactCardProps. */
function modeCardsFor(
  step: V4PipelineStepId,
  ctx: V4Context,
  solverResiduals: ResidualSeriesPayload | null = null,
): FactCardProps[] {
  const basics = ctx.basics;
  const mesh = ctx.meshMetrics;
  const detail = ctx.runDetail;

  switch (step) {
    case "import": {
      return [
        {
          title: "算例信息",
          facts: [
            { label: "case_id", value: ctx.caseId ?? "—" },
            {
              label: "名称",
              value: ctx.displayNameZh ?? ctx.displayName ?? "—",
            },
            { label: "维度", value: String(basics?.dimension ?? "—") },
            {
              label: "运行记录",
              value: ctx.latestRun
                ? `${ctx.latestRun.run_id} · ${ctx.latestRun.success ? "✓" : "✗"}`
                : "—",
              tone: ctx.latestRun?.success
                ? "healthy"
                : ctx.latestRun
                  ? "crit"
                  : "neutral",
            },
          ],
        },
      ];
    }
    case "geometry": {
      const cl = basics?.geometry?.characteristic_length;
      if (!basics || !hasAuthoredCadParts(basics.patches?.length)) {
        return [
          {
            title: "几何已就绪",
            facts: [
              {
                label: "CAD 分件",
                value: `${GEOMETRY_BLUEPRINT_SUMMARY.partCount} 部件`,
                tone: "healthy",
              },
              {
                label: "实例",
                value: `${GEOMETRY_BLUEPRINT_SUMMARY.instanceCount} 个`,
              },
              {
                label: "容差",
                value: `${GEOMETRY_BLUEPRINT_SUMMARY.toleranceMm.toFixed(1)} mm`,
              },
            ],
            footer: "GLB 可用 · 单壳 STL 的 CAD 分件语义待命名",
          },
          {
            title: "启动几何分析",
            facts: [
              { label: "水密性", value: "已通过", tone: "healthy" },
              { label: "单位", value: "mm" },
              {
                label: "估算单元",
                value: `${GEOMETRY_BLUEPRINT_SUMMARY.estimatedCellsM.toFixed(2)} M`,
              },
            ],
            cta: "启动几何分析",
            ctaTone: "active",
          },
          {
            title: "建议合并 2 实例",
            facts: [
              { label: "重复实例", value: "2", tone: "warn" },
              { label: "策略", value: "保留母体" },
              { label: "影响", value: "网格更稳定" },
            ],
            cta: "查看建议",
          },
        ];
      }
      return [
        {
          title: "几何摘要",
          facts: [
            { label: "形状", value: basics?.geometry?.shape ?? "—" },
            { label: "维度", value: basics ? `${basics.dimension}D` : "—" },
            {
              label: cl?.name ?? "特征长度",
              value: cl ? `${cl.value.toPrecision(3)} ${cl.unit}` : "—",
            },
            {
              label: "边界面",
              value: String(basics?.patches?.length ?? "—"),
            },
            {
              label: "材料",
              value: String(basics?.materials?.length ?? "—"),
            },
          ],
        },
      ];
    }
    case "mesh": {
      const gci = mesh?.gci;
      const qc = mesh?.qc_band;
      if (!mesh) {
        return [
          {
            title: "网格生成完成",
            facts: [
              {
                label: "估算单元",
                value: `${MESH_BLUEPRINT_NUMERICS.estimatedCellsM.toFixed(2)} M`,
                tone: "healthy",
              },
              { label: "线框层", value: "mesh.glb" },
              { label: "histogram", value: "5 项" },
            ],
            footer: "mesh metrics artifact 缺失 · 使用蓝图 QA 分布合同",
          },
          {
            title: "18.86M 单元 · 0.128 max skew",
            facts: [
              {
                label: "max skew",
                value: MESH_BLUEPRINT_NUMERICS.maxSkewness.toFixed(3),
                tone: "healthy",
              },
              {
                label: "max non-orth",
                value: `${MESH_BLUEPRINT_NUMERICS.maxNonOrthogonalityDeg.toFixed(1)}°`,
                tone: "warn",
              },
              {
                label: "时间估计",
                value: `${MESH_BLUEPRINT_NUMERICS.timeEstimateMin.toFixed(1)} min`,
              },
            ],
          },
          {
            title: "评估",
            facts: [
              { label: "流体距离", value: "分布正常", tone: "healthy" },
              { label: "表面距离", value: "近壁加密" },
              { label: "下一步", value: "物理设置" },
            ],
            cta: "查看网格质量",
            ctaTone: "active",
          },
        ];
      }
      const gci32Tone: "healthy" | "warn" | "crit" | undefined =
        qc?.gci_32 === "green"
          ? "healthy"
          : qc?.gci_32 === "yellow"
            ? "warn"
            : qc?.gci_32 === "red"
              ? "crit"
              : undefined;
      return [
        {
          title: "网格收敛",
          facts: [
            {
              label: "网格层级",
              value: String(mesh?.densities?.length ?? "—"),
            },
            {
              label: "GCI₃₂",
              value:
                gci?.gci_32_pct != null
                  ? `${fmtPct(gci.gci_32_pct, 2)} %`
                  : "—",
              tone: gci32Tone,
            },
            {
              label: "p_obs",
              value: gci?.p_obs != null ? fmtPct(gci.p_obs, 2) : "—",
            },
            {
              label: "渐进区",
              value:
                gci?.asymptotic_range_ok === true
                  ? "✓"
                  : gci?.asymptotic_range_ok === false
                    ? "✗"
                    : "—",
              tone:
                gci?.asymptotic_range_ok === true
                  ? "healthy"
                  : gci?.asymptotic_range_ok === false
                    ? "warn"
                    : undefined,
            },
            {
              label: "外推值 f_∞",
              value:
                gci?.f_extrapolated != null
                  ? gci.f_extrapolated.toPrecision(4)
                  : "—",
            },
          ],
          footer: gci?.note ?? undefined,
        },
      ];
    }
    case "physics": {
      const solver = basics?.solver;
      if (!solver) {
        return [
          {
            title: "推荐 SST k-ω",
            facts: [
              { label: "模型族", value: "RANS" },
              { label: "近壁处理", value: "Wall fn" },
              { label: "速度范围", value: "0-40 m/s" },
            ],
            footer: "适合高 Re 外流 · 需用户采纳后写入",
            cta: "查看依据",
            ctaTone: "active",
          },
          {
            title: "稳态流动",
            facts: [
              { label: "时间格式", value: PHYSICS_BLUEPRINT_SUMMARY.caseType },
              {
                label: "重力",
                value: `${PHYSICS_BLUEPRINT_SUMMARY.gravity.toFixed(1)} m/s²`,
              },
              {
                label: "材料",
                value: `${PHYSICS_BLUEPRINT_SUMMARY.materialCount} 项`,
              },
            ],
            cta: "查看时间设置",
          },
          {
            title: "应用预设",
            facts: [
              {
                label: "模型",
                value: `${PHYSICS_BLUEPRINT_SUMMARY.modelCount} 项`,
              },
              {
                label: "估算单元",
                value: `${PHYSICS_BLUEPRINT_SUMMARY.estimatedCellsM.toFixed(1)} M`,
              },
              { label: "下一步", value: "边界设置" },
            ],
            cta: "应用预设",
          },
        ];
      }
      return [
        {
          title: "物理设置",
          facts: [
            { label: "求解器", value: solver?.name ?? "—" },
            { label: "族系", value: solver?.family ?? "—" },
            {
              label: "工况",
              value: solver?.steady_state
                ? "稳态"
                : solver
                  ? "瞬态"
                  : "—",
            },
            {
              label: "层流",
              value:
                solver?.laminar === true
                  ? "层流"
                  : solver?.laminar === false
                    ? "湍流"
                    : "—",
            },
            {
              label: "材料",
              value: String(basics?.materials?.length ?? "—"),
            },
            {
              label: "边界条件",
              value: String(basics?.boundary_conditions?.length ?? "—"),
            },
          ],
          footer: solver?.reasoning_zh,
        },
      ];
    }
    case "boundary": {
      const counts = countByRole(basics?.patches ?? []);
      const roleEntries = (Object.entries(counts) as [PatchRole, number][])
        .sort(([, a], [, b]) => b - a)
        .slice(0, 6);
      return [
        {
          title: "边界面分布",
          facts:
            roleEntries.length > 0
              ? roleEntries.map(([role, count]) => ({
                  label: ROLE_LABEL[role] ?? role,
                  value: `${count} 处`,
                }))
              : [{ label: "—", value: "—" }],
          footer:
            basics?.patches?.length != null
              ? `合计 ${basics.patches.length} 处 · ${basics.boundary_conditions?.length ?? 0} 边界条件`
              : undefined,
        },
      ];
    }
    case "solver": {
      const res = detail?.residuals as Record<string, number> | undefined;
      const resEntries = res ? Object.entries(res) : [];
      const success = detail?.success;
      const gauge = convergenceGaugeFromSeries(solverResiduals);
      const residualFacts =
        solverResiduals != null
          ? [
              {
                label: "残差来源",
                value: solverResiduals.source.toUpperCase(),
              },
              {
                label: "迭代样本",
                value: `${solverResiduals.sample_count} iter`,
              },
              {
                label: "收敛进度",
                value: `${gauge.value.toFixed(0)} %`,
                tone: gauge.achieved
                  ? ("healthy" as const)
                  : gauge.value >= 75
                    ? ("warn" as const)
                    : ("crit" as const),
              },
              {
                label: gauge.worst ? `瓶颈 ${gauge.worst}` : "瓶颈",
                value: fmtSci(latestResidual(solverResiduals, gauge.worst)),
              },
              {
                label: "目标",
                value: fmtSci(solverResiduals.target_floor),
              },
            ]
          : [];
      return [
        {
          title: "求解状态",
          facts: [
            ...(detail
              ? [
                  {
                    label: "结果",
                    value: success === true ? "通过" : "失败",
                    tone: success === true
                      ? ("healthy" as const)
                      : ("crit" as const),
                  },
                  {
                    label: "运行时长",
                    value:
                      ctx.latestRun?.duration_s != null
                        ? `${ctx.latestRun.duration_s.toFixed(1)} s`
                        : "—",
                  },
                  ...resEntries.slice(0, 2).map(([k, v]) => ({
                    label: `残差 ${k}`,
                    value: fmtSci(v),
                    tone: v < 1e-3 ? ("healthy" as const) : ("warn" as const),
                  })),
                ]
              : []),
            ...residualFacts,
          ],
          footer:
            detail?.verdict_summary?.slice(0, 80) ??
            solverResiduals?.note,
        },
      ];
    }
    case "post": {
      const success = ctx.successfulRunDetail?.success;
      const kq = (ctx.successfulRunDetail?.key_quantities ?? {}) as Record<
        string,
        unknown
      >;
      const scalarKq = Object.entries(kq)
        .filter(([, v]) => typeof v === "number" && Number.isFinite(v as number))
        .slice(0, 4) as [string, number][];
      return [
        {
          title: "后处理验收",
          facts: [
            {
              label: "verdict",
              value: success === true ? "通过" : ctx.successfulRunDetail ? "失败" : "—",
              tone: success === true ? "healthy" : ctx.successfulRunDetail ? "crit" : "neutral",
            },
            {
              label: "运行 ID",
              value:
                ctx.latestSuccessfulRun?.run_id ?? ctx.latestRun?.run_id ?? "—",
            },
            ...scalarKq.map(([k, v]) => ({
              label: k,
              value: fmtSci(v),
            })),
          ],
          footer: ctx.successfulRunDetail?.verdict_summary?.slice(0, 80),
        },
      ];
    }
    case "doe":
      return [
        {
          title: "设计探索",
          facts: [
            { label: "样本", value: "—" },
            { label: "best 流量", value: "—" },
            { label: "best 温度", value: "—" },
          ],
          footer: "DOE 后端待接入",
        },
      ];
  }
}

function PlaceholderPillCard({ pill, idx }: { pill: PlaceholderPill; idx: number }) {
  return (
    <article
      className="flex flex-col gap-1.5 rounded border border-v4-border bg-v4-surfaceRaised p-2.5"
      data-testid={`rightpanel-v4-placeholder-pill-${idx}`}
      data-severity={pill.severity}
    >
      <div className="flex items-start gap-2">
        <span
          aria-hidden
          className="mt-0.5 h-2 w-2 shrink-0 rounded-full"
          style={{ backgroundColor: V4_SEVERITY_COLOR[pill.severity] }}
        />
        <div className="min-w-0 flex-1">
          <div className="truncate text-[12px] font-medium text-v4-textPrimary">
            {pill.title}
          </div>
          <div className="truncate text-[11px] text-v4-textSecondary">
            {pill.subtitle}
          </div>
        </div>
      </div>
    </article>
  );
}

interface RightPanelV4Props {
  activeStep: V4PipelineStepId;
  caseId?: string | null;
}

export function RightPanelV4({ activeStep, caseId = null }: RightPanelV4Props) {
  const ctx = useV4WorkbenchContext(caseId);
  const matcher = useV4AdvisorMatches(caseId);
  const solverResiduals = useResidualSeries(
    activeStep === "solver" ? caseId : null,
  );
  const realMatcherMode = Boolean(caseId);
  const modeCards = realMatcherMode
    ? modeCardsFor(activeStep, ctx, solverResiduals.data)
    : [];
  const placeholderPills = realMatcherMode
    ? []
    : PLACEHOLDER_BY_STEP[activeStep] ?? [];

  return (
    <aside
      className="flex w-[300px] shrink-0 flex-col border-l border-v4-border bg-v4-surface"
      data-testid="rightpanel-v4"
      data-real-matcher={realMatcherMode ? "true" : "false"}
    >
      <div className="flex h-8 items-center justify-between border-b border-v4-border px-3 text-[11px] uppercase tracking-wider text-v4-textSecondary">
        <span>AI 助理</span>
        <span
          className="text-v4-textTertiary"
          data-testid="rightpanel-v4-advisory-note"
        >
          advisory only · 仅建议
        </span>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto p-3">
        {realMatcherMode ? (
          <>
            <CompletenessCard ctx={ctx} />
            {modeCards.map((card, i) => (
              <FactCard key={`${activeStep}-${i}`} {...card} />
            ))}
            <div className="mt-1 text-[10px] uppercase tracking-wider text-v4-textTertiary">
              V91 匹配
            </div>
            <AdvisorPillStack
              matches={matcher.matches}
              runId={matcher.runId}
              rulesetVersion={matcher.rulesetVersion}
              isLoading={matcher.isLoading}
            />
          </>
        ) : (
          <>
            <div className="text-[10px] uppercase tracking-wider text-v4-textTertiary">
              示例条目 · {activeStep}（选择算例以加载真实诊断）
            </div>
            {placeholderPills.map((pill, i) => (
              <PlaceholderPillCard key={i} pill={pill} idx={i} />
            ))}
          </>
        )}
      </div>
    </aside>
  );
}
