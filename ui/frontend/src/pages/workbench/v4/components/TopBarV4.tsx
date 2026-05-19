/**
 * V4 · TopBar · 32px · per UI-SPEC §2.1 · Phase B real backend wiring.
 *
 * LEFT  : wordmark "CFD 全流程工作台"
 * CENTER: breadcrumb · real `case_name ▾ · run_id ▾ · 计算 HH:MM:SS · Cluster`
 *         · clicking picker chevrons opens a (TODO Phase B-2) switcher
 * RIGHT : AI 助理 status pill · brand-dot indicator
 *
 * Data source: useV4WorkbenchContext (single fan-out hook).
 * Graceful: caseId=null → static placeholder strings; backend down →
 * displays caseId raw + dashes.
 */
import { V4_PALETTE } from "@/theme/industrial_minimalist";
import {
  convergenceGaugeFromSeries,
  useResidualSeries,
} from "../hooks/useResidualSeries";
import { useV4WorkbenchContext } from "../hooks/useV4WorkbenchContext";

interface TopBarV4Props {
  caseId?: string;
}

function Chevron() {
  return (
    <svg
      width="8"
      height="8"
      viewBox="0 0 24 24"
      className="inline-block opacity-70"
      aria-hidden
    >
      <path
        d="M6 9l6 6 6-6"
        stroke="currentColor"
        strokeWidth="2.5"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function Bullet() {
  return <span className="text-v4-textTertiary/60">·</span>;
}

function MenuIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden>
      <path
        d="M2 4h12M2 8h12M2 12h12"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
    </svg>
  );
}

const PLACEHOLDER_CASE = "选择算例";
const PLACEHOLDER_RUN = "—";
const STATIC_CLUSTER = "Cluster-01 [128 核]"; // cluster meta isn't in backend yet

function compactCaseLabel(caseId: string | undefined, display: string | null): string {
  if (display && display !== caseId) return display;
  if (!caseId) return PLACEHOLDER_CASE;
  const importedMatch = caseId.match(/^imported_.*?_([0-9a-f]{8})$/i);
  if (importedMatch) return `Imported · ${importedMatch[1]}`;
  return caseId.length > 28 ? `${caseId.slice(0, 12)}…${caseId.slice(-8)}` : caseId;
}

export function TopBarV4({ caseId }: TopBarV4Props) {
  const ctx = useV4WorkbenchContext(caseId ?? null);
  const residuals = useResidualSeries(caseId ?? null);
  const gauge = convergenceGaugeFromSeries(residuals.data);

  const caseLabel = compactCaseLabel(
    caseId,
    ctx.displayNameZh ?? ctx.displayName ?? null,
  );
  const projectLabel = caseId ? "Imported CFD" : "V4 工作台";
  const runLabel = ctx.latestRun?.run_id
    ? ctx.latestRun.run_id.slice(0, 10)
    : residuals.data && residuals.data.source !== "empty"
      ? `${residuals.data.source} · ${residuals.data.sample_count} iter`
      : PLACEHOLDER_RUN;
  const elapsedLabel = ctx.elapsedDisplay;
  const runState =
    residuals.data && residuals.data.source !== "empty"
      ? gauge.achieved
        ? "已收敛"
        : `收敛中 ${gauge.value.toFixed(0)}%`
      : ctx.latestRun
        ? ctx.latestRun.success
          ? "完成"
          : "失败"
        : "待运行";
  const runStateTone =
    residuals.data && residuals.data.source !== "empty"
      ? gauge.achieved
        ? V4_PALETTE.healthy
        : V4_PALETTE.active
      : ctx.latestRun?.success
        ? V4_PALETTE.healthy
        : ctx.latestRun
          ? V4_PALETTE.crit
          : V4_PALETTE.textTertiary;

  return (
    <header
      className="flex h-8 shrink-0 items-center justify-between border-b border-v4-border bg-v4-shell px-3 text-[11px]"
      data-testid="topbar-v4"
      data-backend-connected={ctx.hasBackend ? "true" : "false"}
    >
      {/* LEFT · wordmark */}
      <div className="flex w-[220px] items-center gap-3">
        <button
          type="button"
          className="flex h-6 w-6 items-center justify-center border-r border-v4-border pr-2 text-v4-textSecondary hover:text-v4-textPrimary"
          title="工作台菜单"
          data-testid="topbar-v4-menu"
        >
          <MenuIcon />
        </button>
        <span className="whitespace-nowrap text-[12px] font-medium text-v4-textPrimary">
          CFD 全流程工作台
        </span>
      </div>

      {/* CENTER · breadcrumb */}
      <div className="flex min-w-0 flex-1 items-center justify-center gap-2 font-mono">
        <span className="flex min-w-0 shrink-0 items-center gap-1.5 whitespace-nowrap text-v4-textSecondary">
          <span className="text-v4-textTertiary">项目</span>
          <span className="max-w-[14ch] truncate text-v4-textPrimary">
            {projectLabel}
          </span>
        </span>
        <Bullet />
        <button
          type="button"
          className="flex min-w-0 shrink items-center gap-1 rounded px-1.5 py-0.5 text-v4-textPrimary transition-colors hover:bg-v4-surfaceRaised disabled:opacity-60"
          data-testid="topbar-v4-case-picker"
          title={caseId ?? "未选择算例"}
        >
          <span className="shrink-0 text-v4-textTertiary">案例</span>
          <span className="max-w-[18ch] truncate">{caseLabel}</span>
          <Chevron />
        </button>
        <Bullet />
        <button
          type="button"
          className="flex min-w-0 shrink items-center gap-1 rounded px-1.5 py-0.5 text-v4-textPrimary transition-colors hover:bg-v4-surfaceRaised disabled:opacity-60"
          data-testid="topbar-v4-run-picker"
          disabled={!ctx.latestRun && !residuals.data}
          title={runLabel}
        >
          <span className="shrink-0 text-v4-textTertiary">运行</span>
          <span className="max-w-[16ch] truncate">{runLabel}</span>
          <Chevron />
        </button>
        <Bullet />
        <span
          className="inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded border border-v4-border bg-v4-surfaceRaised px-2 py-0.5"
          data-testid="topbar-v4-run-state"
        >
          <span
            aria-hidden
            className="h-1.5 w-1.5 rounded-full"
            style={{ backgroundColor: runStateTone }}
          />
          <span className="text-v4-textPrimary">{runState}</span>
        </span>
        <Bullet />
        <span className="shrink-0 whitespace-nowrap text-v4-textSecondary">
          <span className="text-v4-textTertiary">计算 </span>
          <span
            className="tabular-nums text-v4-textPrimary"
            data-testid="topbar-v4-elapsed"
          >
            {elapsedLabel}
          </span>
        </span>
        <Bullet />
        <span className="shrink-0 whitespace-nowrap text-v4-textSecondary">
          <span className="text-v4-textTertiary">资源 </span>
          {STATIC_CLUSTER}
        </span>
      </div>

      {/* RIGHT · AI 助理 */}
      <div className="flex w-[180px] items-center justify-end gap-2">
        <button
          type="button"
          className="flex items-center gap-1.5 rounded border border-v4-active/60 bg-v4-surfaceRaised px-2 py-0.5 text-v4-active transition-colors hover:border-v4-active"
          data-testid="topbar-v4-ai-toggle"
          title="AI 建议只读入口"
        >
          <span aria-hidden className="text-[11px]">✦</span>
          AI 副驾
        </button>
      </div>
    </header>
  );
}
