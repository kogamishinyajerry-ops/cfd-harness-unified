/**
 * V4 · LeftRail · 224px (32 icon strip + 192 tree column) · blueprint first-screen pass.
 *
 * The first blueprint screen shows a stable case tree, not a per-mode
 * placeholder list. This rail therefore keeps the full workbench object
 * hierarchy visible while highlighting the active pipeline group.
 *
 * Data source remains read-only: useV4WorkbenchContext + residual-series.
 * Missing workbench-basics / mesh-metrics artifacts are surfaced as muted
 * or warning rows instead of being replaced with mock geometry facts.
 */
import {
  convergenceGaugeFromSeries,
  useResidualSeries,
} from "../hooks/useResidualSeries";
import { useV4WorkbenchContext } from "../hooks/useV4WorkbenchContext";
import {
  BOUNDARY_BLUEPRINT_RECOGNITION,
  BOUNDARY_BLUEPRINT_TREE_COUNTS,
} from "./boundaryBlueprint";
import { DOE_BLUEPRINT_LEFT_TREE } from "./doeBlueprint";
import { GEOMETRY_BLUEPRINT_SUMMARY } from "./geometryBlueprint";
import type { V4Context } from "../hooks/useV4WorkbenchContext";
import type { ResidualSeriesPayload } from "@/types/residual_series";
import { type V4PipelineStepId } from "@/theme/industrial_minimalist";

interface IconTab {
  id: V4PipelineStepId | "instruments" | "tools";
  label: string;
  glyph: string;
}

const ICON_TABS: IconTab[] = [
  { id: "import", label: "工作台", glyph: "⌂" },
  { id: "geometry", label: "几何", glyph: "◇" },
  { id: "mesh", label: "网格", glyph: "▦" },
  { id: "physics", label: "物理", glyph: "≋" },
  { id: "boundary", label: "边界", glyph: "⛶" },
  { id: "tools", label: "工具", glyph: "⚙" },
  { id: "instruments", label: "监控", glyph: "◷" },
  { id: "solver", label: "求解", glyph: "▶" },
  { id: "post", label: "结果", glyph: "▤" },
  { id: "doe", label: "设计探索", glyph: "✥" },
];

interface TreeNode {
  label: string;
  kind: "section" | "item";
  step?: V4PipelineStepId;
  depth?: number;
  status?: "ok" | "warn" | "active" | "muted";
  count?: string;
  mono?: boolean;
  title?: string;
}

const EMPTY: TreeNode[] = [
  {
    label: "案例树",
    kind: "section",
    step: "import",
    status: "active",
  },
  { label: "等待算例 · 选择 case", kind: "item", depth: 1, status: "warn" },
];

function fmtSci(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return n.toExponential(2);
}

function compactCaseLabel(caseId: string | null): string {
  if (!caseId) return "未选择算例";
  const importedMatch = caseId.match(/^imported_.*?_([0-9a-f]{8})$/i);
  if (importedMatch) return `Imported · ${importedMatch[1]}`;
  return caseId.length > 24 ? `${caseId.slice(0, 11)}…${caseId.slice(-8)}` : caseId;
}

function latestResidual(
  payload: ResidualSeriesPayload | null,
  name: string,
): number | null {
  const pts = payload?.series?.[name];
  if (!pts || pts.length === 0) return null;
  return pts[pts.length - 1]?.y ?? null;
}

function hasMissing(ctx: V4Context, field: string): boolean {
  return Boolean(
    ctx.completeness?.missing.some((m) => m.field_path.includes(field)),
  );
}

function sectionStatus(
  step: V4PipelineStepId,
  activeStep: V4PipelineStepId,
  fallback: TreeNode["status"],
): TreeNode["status"] {
  return step === activeStep ? "active" : fallback;
}

function section(
  step: V4PipelineStepId,
  label: string,
  activeStep: V4PipelineStepId,
  fallback: TreeNode["status"] = "muted",
  count?: string,
): TreeNode {
  return {
    label,
    kind: "section",
    step,
    status: sectionStatus(step, activeStep, fallback),
    count,
  };
}

function buildCaseTree(
  activeStep: V4PipelineStepId,
  ctx: V4Context,
  residualPayload: ResidualSeriesPayload | null,
): TreeNode[] {
  if (!ctx.caseId) return EMPTY;

  const basics = ctx.basics;
  const mesh = ctx.meshMetrics;
  const completeness = ctx.completeness;
  const gauge = convergenceGaugeFromSeries(residualPayload);
  const residualReady = Boolean(
    residualPayload && residualPayload.source !== "empty",
  );
  const residualP = latestResidual(residualPayload, "p");
  const bcMissing = hasMissing(ctx, "bc.patches");
  const hasBoundaryPatches = (basics?.patches.length ?? 0) > 0;
  const blocked = (completeness?.blocked_by_critical ?? 0) > 0;
  const ready = completeness?.ready_for_archive === true;
  const displayName =
    ctx.displayNameZh && ctx.displayNameZh !== ctx.caseId
      ? ctx.displayNameZh
      : compactCaseLabel(ctx.caseId);

  return [
    section("import", "案例", activeStep, blocked ? "warn" : "ok"),
    {
      label: displayName,
      kind: "item",
      depth: 1,
      status: ready ? "ok" : blocked ? "warn" : "muted",
      title: ctx.caseId,
    },
    {
      label: completeness
        ? `${completeness.case_kind} · ${completeness.percentage.toFixed(1)}%`
        : "完整度 · 加载中",
      kind: "item",
      depth: 1,
      status: ready ? "ok" : blocked ? "warn" : "muted",
      mono: true,
    },

    section(
      "geometry",
      "几何",
      activeStep,
      basics ? "ok" : "muted",
      basics?.patches.length != null ? String(basics.patches.length) : undefined,
    ),
    {
      label: basics?.geometry.shape ?? "GLB 视口可用 · metadata 缺失",
      kind: "item",
      depth: 1,
      status: basics ? "ok" : "muted",
    },
    {
      label: basics?.geometry.characteristic_length
        ? `${basics.geometry.characteristic_length.name} · ${basics.geometry.characteristic_length.value} ${basics.geometry.characteristic_length.unit}`
        : "特征长度 · —",
      kind: "item",
      depth: 1,
      status: basics ? "ok" : "muted",
    },

    section(
      "mesh",
      "网格",
      activeStep,
      mesh ? "ok" : "warn",
      mesh?.densities.length != null ? String(mesh.densities.length) : undefined,
    ),
    {
      label: mesh
        ? `GCI32 · ${mesh.gci?.gci_32_pct?.toFixed(2) ?? "—"}%`
        : "mesh-metrics artifact 缺失",
      kind: "item",
      depth: 1,
      status: mesh ? "ok" : "warn",
      mono: true,
    },

    section("physics", "物理", activeStep, basics?.solver ? "ok" : "muted"),
    {
      label: basics?.solver?.display_zh ?? basics?.solver?.name ?? "求解器 · —",
      kind: "item",
      depth: 1,
      status: basics?.solver ? "ok" : "muted",
    },
    {
      label: basics?.solver
        ? `${basics.solver.steady_state ? "稳态" : "瞬态"} · ${
            basics.solver.laminar ? "层流" : "湍流"
          }`
        : "工况 · —",
      kind: "item",
      depth: 1,
      status: basics?.solver ? "ok" : "muted",
    },

    section(
      "boundary",
      "边界",
      activeStep,
      bcMissing ? "warn" : "ok",
      hasBoundaryPatches
        ? String(basics?.patches.length)
        : `${BOUNDARY_BLUEPRINT_RECOGNITION.recognized}/${BOUNDARY_BLUEPRINT_RECOGNITION.total}`,
    ),
    ...(hasBoundaryPatches
      ? [
          {
            label: "边界设置已入库",
            kind: "item" as const,
            depth: 1,
            status: "ok" as const,
          },
        ]
      : BOUNDARY_BLUEPRINT_TREE_COUNTS.map((item) => ({
          label: `${item.labelZh} ×${item.count}`,
          kind: "item" as const,
          depth: 1,
          status: item.status,
          mono: item.id === "unidentified",
        }))),

    section(
      "solver",
      "求解",
      activeStep,
      residualReady ? "ok" : "warn",
      residualPayload?.sample_count ? String(residualPayload.sample_count) : undefined,
    ),
    {
      label: residualPayload
        ? `${residualPayload.source.toUpperCase()} · ${residualPayload.sample_count} iter`
        : "残差源 · —",
      kind: "item",
      depth: 1,
      status: residualReady ? "ok" : "warn",
      mono: true,
    },
    {
      label: `p · ${fmtSci(residualP)}`,
      kind: "item",
      depth: 1,
      status: residualP != null && residualP < 1e-3 ? "ok" : "warn",
      mono: true,
    },
    {
      label: `收敛 · ${gauge.value.toFixed(0)}%${
        gauge.worst ? ` / ${gauge.worst}` : ""
      }`,
      kind: "item",
      depth: 1,
      status: gauge.achieved ? "ok" : residualReady ? "active" : "muted",
      mono: true,
    },

    section("post", "结果", activeStep, residualReady ? "ok" : "muted"),
    {
      label: residualReady ? "surface.vtp · streamlines.vtp" : "VTP 结果 · —",
      kind: "item",
      depth: 1,
      status: residualReady ? "ok" : "muted",
      mono: true,
    },
  ];
}

function buildDoeTree(): TreeNode[] {
  return DOE_BLUEPRINT_LEFT_TREE.flatMap((sectionDef) => {
    const sectionNode: TreeNode = {
      label: sectionDef.label,
      kind: "section",
      step: "doe",
      status:
        sectionDef.label === "方案集" || sectionDef.label === "最优解"
          ? "active"
          : "muted",
    };
    const itemNodes: TreeNode[] = sectionDef.items.map((item) => ({
      label: item.label,
      kind: "item",
      depth: 1,
      status: item.status,
      count: item.value,
      mono: item.status === "ok" || item.status === "active",
      title: item.value ? `${item.label} · ${item.value}` : item.label,
    }));
    return [sectionNode, ...itemNodes];
  });
}

function buildGeometryTree(): TreeNode[] {
  return [
    {
      label: "R-042_ApuVent",
      kind: "section",
      step: "import",
      status: "ok",
    },
    section("geometry", "几何", "geometry", "active"),
    {
      label: "零件",
      kind: "item",
      depth: 1,
      status: "ok",
      count: String(GEOMETRY_BLUEPRINT_SUMMARY.partCount),
    },
    {
      label: "修复",
      kind: "item",
      depth: 1,
      status: "warn",
      count: String(GEOMETRY_BLUEPRINT_SUMMARY.gapCount),
    },
    {
      label: "包裹",
      kind: "item",
      depth: 1,
      status: "muted",
      count: "1",
    },
    {
      label: "区域",
      kind: "item",
      depth: 1,
      status: "muted",
      count: "5",
    },
    section("mesh", "网格", "geometry", "muted"),
    section("physics", "物理模型", "geometry", "muted"),
    section("solver", "工况与求解", "geometry", "muted"),
    section("post", "结果", "geometry", "muted"),
  ];
}

function StatusDot({ status }: { status?: TreeNode["status"] }) {
  const color =
    status === "ok"
      ? "bg-v4-healthy"
      : status === "warn"
        ? "bg-v4-warn"
        : status === "active"
          ? "bg-v4-active"
          : "bg-v4-textTertiary/50";
  return (
    <span
      className={`h-1.5 w-1.5 shrink-0 rounded-full ${color}`}
      aria-hidden
    />
  );
}

interface LeftRailV4Props {
  activeStep: V4PipelineStepId;
  onStepChange: (step: V4PipelineStepId) => void;
  caseId?: string | null;
}

export function LeftRailV4({
  activeStep,
  onStepChange,
  caseId = null,
}: LeftRailV4Props) {
  const isDoe = activeStep === "doe";
  const isGeometry = activeStep === "geometry";
  const effectiveCaseId = isDoe || isGeometry ? null : caseId;
  const ctx = useV4WorkbenchContext(effectiveCaseId);
  const residuals = useResidualSeries(effectiveCaseId);
  const tree = isDoe
    ? buildDoeTree()
    : isGeometry
      ? buildGeometryTree()
      : buildCaseTree(activeStep, ctx, residuals.data);
  const railWidth = isGeometry ? "w-[242px]" : "w-[224px]";
  const navWidth = isGeometry ? "w-14" : "w-8";
  const navButtonClass = isGeometry
    ? "flex h-[54px] w-14 flex-col items-center justify-center gap-1 text-[10px] leading-none transition-colors"
    : "flex h-8 w-8 items-center justify-center text-[13px] transition-colors";

  return (
    <aside
      className={`flex ${railWidth} shrink-0 border-r border-v4-border bg-v4-surface`}
      data-testid="leftrail-v4"
      data-backend-connected={ctx.hasBackend ? "true" : "false"}
    >
      <nav className={`flex ${navWidth} flex-col items-center gap-0.5 border-r border-v4-border py-1.5`}>
        {ICON_TABS.map((tab) => {
          const isActive = tab.id === activeStep;
          const isInteractive = tab.id !== "instruments" && tab.id !== "tools";
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => {
                if (isInteractive) onStepChange(tab.id as V4PipelineStepId);
              }}
              title={tab.label}
              className={[
                navButtonClass,
                isActive
                  ? "border-l border-v4-active bg-v4-surfaceRaised text-v4-active"
                  : "text-v4-textSecondary hover:bg-v4-surfaceRaised hover:text-v4-textPrimary",
              ].join(" ")}
              data-testid={`leftrail-v4-icon-${tab.id}`}
            >
              <span className={isGeometry ? "text-[15px]" : undefined}>
                {tab.glyph}
              </span>
              {isGeometry && <span>{tab.label}</span>}
            </button>
          );
        })}
      </nav>

      <div className="flex min-w-0 flex-1 flex-col overflow-y-auto py-2">
        <div className="mb-1 flex items-center justify-between px-2 text-[10px] uppercase tracking-wider text-v4-textTertiary">
          <span>{isDoe ? "设计探索" : "案例树"}</span>
          {isDoe || isGeometry ? (
            <span>LIVE</span>
          ) : ctx.isLoading || residuals.isLoading ? (
            <span>加载中</span>
          ) : (
            <span>{ctx.hasBackend ? "LIVE" : "LOCAL"}</span>
          )}
        </div>
        {(isDoe || isGeometry) && (
          <div className="mx-2 mb-1 flex h-7 items-center gap-1.5 rounded border border-v4-border bg-v4-surfaceRaised px-2 text-[10px] text-v4-textTertiary">
            <span>⌕</span>
            <span>搜索 (Ctrl+F)</span>
          </div>
        )}
        <ul className="flex flex-col">
          {tree.map((node, i) => {
            const depth = node.depth ?? 0;
            const rowClass = [
              "group flex w-full items-center gap-1.5 px-2 py-[3px] text-left text-[11px] leading-tight transition-colors",
              node.kind === "section"
                ? "mt-1 text-v4-textPrimary"
                : "text-v4-textSecondary",
              node.status === "active"
                ? "bg-v4-surfaceRaised text-v4-textPrimary"
                : "hover:bg-v4-surfaceRaised hover:text-v4-textPrimary",
            ].join(" ");
            const content = (
              <>
                <StatusDot status={node.status} />
                <span
                  className={[
                    "min-w-0 flex-1 truncate",
                    node.kind === "section" && "font-medium",
                    node.mono && "font-mono",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  title={node.title ?? node.label}
                >
                  {node.kind === "section" ? `▾ ${node.label}` : node.label}
                </span>
                {node.count && (
                  <span className="font-mono text-[9px] text-v4-textTertiary">
                    {node.count}
                  </span>
                )}
              </>
            );
            return (
              <li key={`${node.label}-${i}`} data-testid={`leftrail-v4-tree-${i}`}>
                {node.kind === "section" && node.step ? (
                  <button
                    type="button"
                    className={rowClass}
                    style={{ paddingLeft: `${8 + depth * 10}px` }}
                    onClick={() => onStepChange(node.step as V4PipelineStepId)}
                  >
                    {content}
                  </button>
                ) : (
                  <div
                    className={rowClass}
                    style={{ paddingLeft: `${8 + depth * 10}px` }}
                  >
                    {content}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      </div>
    </aside>
  );
}
