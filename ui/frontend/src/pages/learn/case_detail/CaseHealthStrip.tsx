// CaseHealthStrip · post-Stage-6 polish.
//
// Single horizontal strip shown directly under the breadcrumb on
// LearnCaseDetailPage. Composes the three "system pulse" endpoints
// (preflight + mesh-metrics + workbench-basics) into a 3-chip status
// bar, so the user knows whether this case is healthy *before* they
// click into a tab.
//
// Each chip is a hyperlink — clicking jumps to the tab where the
// detail lives:
//   - Preflight chip → ?tab=run (RunRail home)
//   - MeshQC chip    → ?tab=mesh (MeshQC home)
//   - Workbench chip → no tab (CaseFrame is page-level above the bar)
//
// Honesty rules: a chip is gray if data unavailable (e.g. case has no
// preflight or mesh-metrics endpoint). We never silently turn that
// into pretend-green.

import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api, ApiError } from "@/api/client";
import type { MeshMetrics } from "@/types/mesh_metrics";
import type { PreflightSummary } from "@/types/preflight";
import type { WorkbenchBasics } from "@/types/workbench_basics";

type ChipTone = "green" | "yellow" | "red" | "gray";

const TONE: Record<ChipTone, { ring: string; bg: string; text: string }> = {
  green: { ring: "border-emerald-700/60", bg: "bg-emerald-950/40", text: "text-emerald-300" },
  yellow: { ring: "border-amber-700/60", bg: "bg-amber-950/40", text: "text-amber-300" },
  red: { ring: "border-rose-700/60", bg: "bg-rose-950/40", text: "text-rose-300" },
  gray: { ring: "border-surface-700", bg: "bg-surface-900/40", text: "text-surface-400" },
};

const TONE_GLYPH: Record<ChipTone, string> = {
  green: "✓",
  yellow: "◐",
  red: "✗",
  gray: "○",
};

export function CaseHealthStrip({ caseId }: { caseId: string }) {
  const wb = useQuery<WorkbenchBasics, ApiError>({
    queryKey: ["workbench-basics", caseId],
    queryFn: () => api.getWorkbenchBasics(caseId),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
  const mesh = useQuery<MeshMetrics, ApiError>({
    queryKey: ["mesh-metrics", caseId],
    queryFn: () => api.getMeshMetrics(caseId),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
  const pre = useQuery<PreflightSummary, ApiError>({
    queryKey: ["preflight", caseId],
    queryFn: () => api.getPreflight(caseId),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  const wbTone = wbToneFrom(wb.data, wb.error);
  const meshTone = meshToneFrom(mesh.data, mesh.error);
  const preTone = preToneFrom(pre.data, pre.error);

  return (
    <div className="mb-6 grid grid-cols-1 gap-2 sm:grid-cols-3">
      <Chip
        tone={wbTone.tone}
        href={`/learn/cases/${encodeURIComponent(caseId)}`}
        title="Stage 2 · 工作台首屏"
        primary={wbTone.primary}
        detail={wbTone.detail}
      />
      <Chip
        tone={preTone.tone}
        href={`/learn/cases/${encodeURIComponent(caseId)}?tab=run`}
        title="Stage 4 · 运行前自检"
        primary={preTone.primary}
        detail={preTone.detail}
      />
      <Chip
        tone={meshTone.tone}
        href={`/learn/cases/${encodeURIComponent(caseId)}?tab=mesh`}
        title="Stage 3 · 网格信任带"
        primary={meshTone.primary}
        detail={meshTone.detail}
      />
    </div>
  );
}

function Chip({
  tone,
  href,
  title,
  primary,
  detail,
}: {
  tone: ChipTone;
  href: string;
  title: string;
  primary: string;
  detail: string;
}) {
  const t = TONE[tone];
  return (
    <Link
      to={href}
      className={`flex items-start gap-3 rounded-md border ${t.ring} ${t.bg} px-3 py-2 transition-colors hover:bg-surface-900/70`}
    >
      <span
        className={`mono mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full border ${t.ring} ${t.text}`}
      >
        {TONE_GLYPH[tone]}
      </span>
      <span className="min-w-0 flex-1">
        <p className="text-[10px] uppercase tracking-wider text-surface-500">{title}</p>
        <p className={`mt-0.5 truncate text-[13px] font-medium ${t.text}`}>{primary}</p>
        <p className="mt-0.5 truncate text-[10px] text-surface-500">{detail}</p>
      </span>
    </Link>
  );
}

// --- Tone derivers -------------------------------------------------------

function wbToneFrom(
  data: WorkbenchBasics | undefined,
  error: ApiError | null,
): { tone: ChipTone; primary: string; detail: string } {
  if (error?.status === 404) {
    return {
      tone: "gray",
      primary: "未编排",
      detail: "knowledge/workbench_basics/<id>.yaml 缺失",
    };
  }
  if (error || !data) {
    return { tone: "gray", primary: "加载中…", detail: "等待 workbench-basics" };
  }
  if (data.schema_drift_warning) {
    return {
      tone: "yellow",
      primary: "schema drift",
      detail: data.schema_drift_warning.slice(0, 60),
    };
  }
  return {
    tone: "green",
    primary: data.geometry.shape,
    detail: `${data.patches.length} patch · ${data.materials.length} material`,
  };
}

function meshToneFrom(
  data: MeshMetrics | undefined,
  error: ApiError | null,
): { tone: ChipTone; primary: string; detail: string } {
  if (error?.status === 404) {
    return { tone: "gray", primary: "无 fixture", detail: "无 mesh sweep" };
  }
  if (error || !data) {
    return { tone: "gray", primary: "加载中…", detail: "等待 mesh-metrics" };
  }
  const band = data.qc_band;
  // Worst verdict across the 4 chips drives the strip color.
  const verdicts = [band.gci_32, band.asymptotic_range, band.richardson_p, band.n_levels];
  const worst: ChipTone =
    (verdicts.includes("red") && "red") ||
    (verdicts.includes("yellow") && "yellow") ||
    (verdicts.every((v) => v === "green") && "green") ||
    "gray";
  const gciPct = data.gci?.gci_32_pct;
  const primary =
    worst === "green"
      ? "GCI 已收敛"
      : worst === "yellow"
        ? "边缘收敛"
        : worst === "red"
          ? "未达渐近域"
          : "无 Richardson";
  const detail =
    gciPct != null
      ? `GCI₃₂=${gciPct.toFixed(1)}% · ${data.densities.length}/4 levels`
      : `${data.densities.length}/4 levels · oscillating`;
  return { tone: worst, primary, detail };
}

function preToneFrom(
  data: PreflightSummary | undefined,
  error: ApiError | null,
): { tone: ChipTone; primary: string; detail: string } {
  if (error?.status === 404) {
    return { tone: "gray", primary: "无 preflight", detail: "—" };
  }
  if (error || !data) {
    return { tone: "gray", primary: "加载中…", detail: "等待 preflight" };
  }
  const tone: ChipTone =
    data.overall === "pass"
      ? "green"
      : data.overall === "partial"
        ? "yellow"
        : data.overall === "fail"
          ? "red"
          : "gray";
  const primary =
    tone === "green"
      ? "全部前置通过"
      : tone === "yellow"
        ? "部分通过"
        : tone === "red"
          ? `${data.counts.fail} 项 fail`
          : "无数据";
  const detail = `${data.counts.pass}P / ${data.counts.partial}M / ${data.counts.fail}F · ${data.n_categories} categories`;
  return { tone, primary, detail };
}
