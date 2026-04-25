// RunRail · Stage 4 GuardedRun MVP — preflight checkpoint visualization
// shown above the Run button in RunTab. Per Codex industrial-workbench
// meeting 2026-04-25 §3 + roadmap S4 (workbench_rollout_roadmap.md).
//
// Source data: `/api/cases/{id}/preflight` which aggregates 5 categories
// (physics / schema / mesh / gold_standard / adapter) into a list of
// checks with pass/fail/partial/skip status + evidence references.
//
// UX rules:
// 1. Header strip shows count rollups + overall verdict chip.
// 2. Each row is collapsible — click to expose evidence + consequence.
// 3. Failures auto-expanded by default (so the user sees the problem
//    without an extra click).
// 4. Categories grouped, ordering matters (physics first to match the
//    Sarah journey "看物理 → 看 schema → 看 mesh" flow).

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api, ApiError } from "@/api/client";
import type {
  PreflightCheck,
  PreflightCategory,
  PreflightStatus,
  PreflightSummary,
} from "@/types/preflight";

// --- Status visual config -----------------------------------------------

const STATUS_COLOR: Record<PreflightStatus, { ring: string; text: string; chip: string }> = {
  pass: {
    ring: "border-emerald-700/60",
    text: "text-emerald-300",
    chip: "bg-emerald-950/40",
  },
  fail: {
    ring: "border-rose-700/60",
    text: "text-rose-300",
    chip: "bg-rose-950/40",
  },
  partial: {
    ring: "border-amber-700/60",
    text: "text-amber-300",
    chip: "bg-amber-950/40",
  },
  skip: {
    ring: "border-surface-700",
    text: "text-surface-500",
    chip: "bg-surface-900/40",
  },
  indeterminate: {
    ring: "border-violet-700/60",
    text: "text-violet-300",
    chip: "bg-violet-950/40",
  },
};

const STATUS_GLYPH: Record<PreflightStatus, string> = {
  pass: "✓",
  fail: "✗",
  partial: "◐",
  skip: "○",
  indeterminate: "?!",
};

const STATUS_LABEL: Record<PreflightStatus, string> = {
  pass: "PASS",
  fail: "FAIL",
  partial: "PARTIAL",
  skip: "SKIP",
  indeterminate: "INDET",
};

const CATEGORY_LABEL: Record<string, string> = {
  physics: "物理前置 · physics",
  schema: "工作台 schema · workbench",
  mesh: "网格 sweep · mesh",
  gold_standard: "金标准 · gold standard",
  adapter: "适配器 · adapter",
};

// Render order: adapter (most fundamental) → schema → gold → physics → mesh
const CATEGORY_ORDER: PreflightCategory[] = [
  "adapter",
  "schema",
  "gold_standard",
  "physics",
  "mesh",
];

// --- Top-level component ------------------------------------------------

export function RunRail({ caseId }: { caseId: string }) {
  const { data, error, isLoading } = useQuery<PreflightSummary, ApiError>({
    queryKey: ["preflight", caseId],
    queryFn: () => api.getPreflight(caseId),
    enabled: !!caseId,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="h-[200px] animate-pulse rounded-md border border-surface-800 bg-surface-900/40" />
    );
  }

  if (error?.status === 404) return null;

  if (error || !data) {
    return (
      <div className="rounded-md border border-amber-700/60 bg-amber-950/30 p-4 text-[12px] text-amber-200">
        ⚠ preflight 加载失败：{error?.message ?? "unknown"}
      </div>
    );
  }

  return (
    <section className="rounded-md border border-surface-800 bg-surface-900/40 p-5">
      <Header data={data} />
      <CategoryGroups checks={data.checks} />
      <Footer data={data} />
    </section>
  );
}

// --- Header strip --------------------------------------------------------

function Header({ data }: { data: PreflightSummary }) {
  const { counts, overall, n_categories } = data;
  const c = STATUS_COLOR[overall];
  return (
    <div className="mb-4">
      <div className="flex items-baseline justify-between gap-3">
        <div>
          <h2 className="card-title">Run Rail · 运行前自检</h2>
          <p className="mt-1 text-[12px] text-surface-500">
            点 Run 之前，harness 已为你跑了 {counts.total} 项前置检查（{n_categories} 类别）。
            <strong className="ml-1 text-surface-300">看到红条不要硬跑</strong>——展开看证据。
          </p>
        </div>
        <span
          className={`mono inline-flex items-center gap-1.5 rounded-md border px-3 py-1 text-[11px] font-medium ${c.ring} ${c.text} ${c.chip}`}
        >
          {STATUS_GLYPH[overall]} 整体 {STATUS_LABEL[overall]}
        </span>
      </div>

      <div className="mt-3 flex flex-wrap gap-2 text-[10px] uppercase tracking-wider">
        <CountChip status="pass" n={counts.pass} />
        <CountChip status="partial" n={counts.partial} />
        <CountChip status="fail" n={counts.fail} />
        <CountChip status="skip" n={counts.skip} />
        <span className="ml-auto text-surface-600">
          mono · {counts.total} checks · {n_categories} categories
        </span>
      </div>
    </div>
  );
}

function CountChip({ status, n }: { status: PreflightStatus; n: number }) {
  if (n === 0) return null;
  const c = STATUS_COLOR[status];
  return (
    <span className={`rounded-sm border px-1.5 py-0.5 ${c.ring} ${c.text} ${c.chip}`}>
      {STATUS_GLYPH[status]} {n} {STATUS_LABEL[status]}
    </span>
  );
}

// --- Category groups -----------------------------------------------------

function CategoryGroups({ checks }: { checks: PreflightCheck[] }) {
  const grouped = useMemo(() => {
    const map = new Map<PreflightCategory, PreflightCheck[]>();
    for (const c of checks) {
      const arr = map.get(c.category) ?? [];
      arr.push(c);
      map.set(c.category, arr);
    }
    // Order
    const ordered: [PreflightCategory, PreflightCheck[]][] = [];
    for (const cat of CATEGORY_ORDER) {
      if (map.has(cat)) {
        ordered.push([cat, map.get(cat)!]);
        map.delete(cat);
      }
    }
    // Append any unknown categories at the end (forward-compat).
    for (const [cat, arr] of map) ordered.push([cat, arr]);
    return ordered;
  }, [checks]);

  return (
    <div className="space-y-3">
      {grouped.map(([cat, items]) => (
        <CategoryGroup key={cat} category={cat} items={items} />
      ))}
    </div>
  );
}

function CategoryGroup({
  category,
  items,
}: {
  category: PreflightCategory;
  items: PreflightCheck[];
}) {
  const passCount = items.filter((i) => i.status === "pass").length;
  return (
    <div className="rounded-md border border-surface-800 bg-surface-950/30">
      <div className="flex items-baseline justify-between border-b border-surface-800 px-3 py-1.5">
        <span className="mono text-[11px] uppercase tracking-wider text-surface-400">
          {CATEGORY_LABEL[category] ?? category}
        </span>
        <span className="mono text-[10px] text-surface-600">
          {passCount}/{items.length}
        </span>
      </div>
      <ul className="divide-y divide-surface-900">
        {items.map((c) => (
          <CheckRow key={c.id} check={c} />
        ))}
      </ul>
    </div>
  );
}

// --- Individual check row -----------------------------------------------

function CheckRow({ check }: { check: PreflightCheck }) {
  const c = STATUS_COLOR[check.status];
  // Auto-expand failures + indeterminate rows so problems are visible
  // at first glance. Pass rows stay collapsed to keep the rail compact.
  const [open, setOpen] = useState(
    check.status === "fail" || check.status === "indeterminate",
  );
  const hasExpand = !!(check.evidence || check.consequence);

  return (
    <li className="px-3 py-2">
      <button
        type="button"
        onClick={() => hasExpand && setOpen((s) => !s)}
        className={`flex w-full items-start gap-3 text-left ${hasExpand ? "cursor-pointer" : "cursor-default"}`}
      >
        <span
          className={`mono mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full border ${c.ring} ${c.text}`}
          aria-label={check.status}
        >
          {STATUS_GLYPH[check.status]}
        </span>
        <span className="flex-1 text-[12px] leading-relaxed text-surface-200">
          {check.label_zh}
          {check.label_en && (
            <span className="ml-1.5 mono text-[10px] text-surface-600">
              {check.label_en}
            </span>
          )}
        </span>
        <span className={`mono text-[10px] uppercase ${c.text}`}>
          {STATUS_LABEL[check.status]}
        </span>
        {hasExpand && (
          <span className="mono text-[10px] text-surface-600">
            {open ? "▾" : "▸"}
          </span>
        )}
      </button>
      {open && (
        <div className="ml-8 mt-1.5 space-y-1.5 text-[11px] leading-relaxed">
          {check.evidence && (
            <p className="text-surface-400">
              <span className="mono mr-1.5 text-surface-600">evidence:</span>
              {check.evidence}
            </p>
          )}
          {check.consequence && (
            <p className="rounded-sm border border-rose-800/40 bg-rose-950/30 px-2 py-1 text-rose-200">
              <span className="mono mr-1.5">consequence:</span>
              {check.consequence}
            </p>
          )}
        </div>
      )}
    </li>
  );
}

// --- Footer -------------------------------------------------------------

function Footer({ data }: { data: PreflightSummary }) {
  const { counts, overall } = data;
  const tone =
    overall === "pass"
      ? "在所有前置都绿之前点 Run 是稳的；如果你在调一个红条，欢迎用 audit_real_run 复现。"
      : overall === "partial"
        ? "存在 partial — 多半是金标准/Mesh fixture 不完整，跑 baseline 没问题但 audit 时要解释。"
        : `存在 ${counts.fail} 项 fail — 上面已展开证据。物理或 schema 红条意味着 audit_real_run 也会失败，建议先解决再跑。`;
  return (
    <p className="mt-4 border-t border-surface-800 pt-3 text-[11px] leading-relaxed text-surface-500">
      <strong className="text-surface-400">读图守则：</strong>
      {tone}
    </p>
  );
}
