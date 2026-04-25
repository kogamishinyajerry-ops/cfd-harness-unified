// Mesh tab: interactive grid-convergence slider over 4 mesh densities,
// per-mesh observable + GCI + Richardson extrapolation.
//
// Extracted 2026-04-25 from LearnCaseDetailPage.tsx (Stage 1 shell-split,
// per Codex industrial-workbench meeting verdict). Behavior unchanged.

import { useQueries } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import type { ContractStatus, ValidationReport } from "@/types/validation";

import { GRID_CONVERGENCE_CASES, STATUS_CLASS, STATUS_TEXT } from "./constants";
import { formatNumber } from "./shared";


export function MeshTab({ caseId }: { caseId: string }) {
  const sweep = GRID_CONVERGENCE_CASES[caseId];

  // Unconditionally create state + queries so the hook call count stays
  // stable regardless of whether this case has a sweep. (React will
  // throw if hook count varies between renders.)
  const densities = sweep?.densities ?? [];
  const [idx, setIdx] = useState(densities.length > 1 ? 2 : 0);

  const reports = useQueries({
    queries: densities.map((d) => ({
      queryKey: ["validation-report", caseId, d.id],
      queryFn: () => api.getValidationReport(caseId, d.id),
      enabled: !!caseId,
      retry: false,
      staleTime: 60_000,
    })),
  });

  if (!sweep) {
    return (
      <div className="rounded-md border border-surface-800 bg-surface-900/40 p-6">
        <p className="card-title mb-2">网格收敛演示尚未为此案例准备</p>
        <p className="text-[13px] leading-relaxed text-surface-400">
          这个案例目前只有一套默认网格的 fixture。目前有网格收敛 sweep 的案例：
          <span className="mono ml-1 text-surface-300">
            {Object.keys(GRID_CONVERGENCE_CASES).join(" · ")}
          </span>
        </p>
      </div>
    );
  }

  const active = reports[idx];
  const activeReport = active?.data as ValidationReport | undefined;
  const activeDensity = densities[idx];
  const loading = reports.some((r) => r.isLoading);

  // Map each density to its (value, verdict) — used for the sparkline.
  const series = reports.map((r, i) => {
    const rep = r.data as ValidationReport | undefined;
    return {
      idx: i,
      label: densities[i].label,
      value: rep?.measurement?.value,
      status: rep?.contract_status ?? "UNKNOWN",
    };
  });

  const goldRef = activeReport?.gold_standard?.ref_value;
  const tol = activeReport?.gold_standard?.tolerance_pct;
  const unit = activeReport?.gold_standard?.unit ?? "";

  return (
    <div className="space-y-6">
      <section className="rounded-md border border-surface-800 bg-surface-900/40 p-6">
        <div className="mb-4 flex items-baseline justify-between">
          <div>
            <h2 className="card-title">网格收敛演示 · Grid Convergence</h2>
            <p className="mt-1 text-[12px] text-surface-500">
              拖动滑块，实时看 {activeReport?.gold_standard?.quantity ?? "key quantity"} 如何随网格密度逼近 gold 值。
            </p>
          </div>
          <span className="mono text-[11px] text-surface-500">
            sweep: {sweep.meshLabel}
          </span>
        </div>

        {/* Density slider */}
        <div className="mb-6">
          <div className="mb-2 flex justify-between text-[11px] text-surface-500">
            {densities.map((d, i) => (
              <button
                key={d.id}
                onClick={() => setIdx(i)}
                className={`rounded-sm px-1.5 py-0.5 transition-colors ${
                  i === idx ? "bg-sky-900/50 text-sky-200" : "hover:text-surface-300"
                }`}
              >
                {d.label}
              </button>
            ))}
          </div>
          <input
            type="range"
            min={0}
            max={densities.length - 1}
            step={1}
            value={idx}
            onChange={(e) => setIdx(Number(e.target.value))}
            className="w-full accent-sky-500"
            aria-label="mesh density"
          />
        </div>

        {/* Active value card */}
        <div className="mb-4 grid gap-4 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
          <div>
            <p className="text-[11px] uppercase tracking-wider text-surface-500">
              测量值
            </p>
            <p className="mono mt-1 text-2xl text-surface-100">
              {loading || active?.data == null
                ? "—"
                : formatNumber(activeReport?.measurement?.value)}
              {unit ? <span className="ml-1 text-[11px] text-surface-500">{unit}</span> : null}
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wider text-surface-500">
              相对 gold 偏差
            </p>
            <p className="mono mt-1 text-2xl text-surface-100">
              {activeReport?.deviation_pct == null ||
              !Number.isFinite(activeReport.deviation_pct)
                ? "—"
                : `${activeReport.deviation_pct >= 0 ? "+" : ""}${activeReport.deviation_pct.toFixed(1)}%`}
            </p>
          </div>
          <div
            className={`rounded-md border px-3 py-1.5 text-[12px] font-medium ${
              activeReport
                ? STATUS_CLASS[activeReport.contract_status]
                : "text-surface-400"
            }`}
          >
            {activeReport ? STATUS_TEXT[activeReport.contract_status] : "加载中…"}
          </div>
        </div>

        {/* Sparkline — convergence trend */}
        <ConvergenceSparkline
          series={series}
          goldRef={goldRef}
          tolPct={tol}
          activeIdx={idx}
        />

        {/* Density description */}
        <div className="mt-4 text-[12px] leading-relaxed text-surface-400">
          <span className="mono text-surface-300">{activeDensity.label}</span>
          <span className="mx-2 text-surface-700">·</span>
          <span className="mono text-surface-500">{activeDensity.n} cells</span>
          <span className="mx-2 text-surface-700">·</span>
          <span className="mono text-surface-500">run_id: {activeDensity.id}</span>
        </div>
      </section>

      <section className="rounded-md border border-surface-800/60 bg-surface-900/20 p-5 text-[12px] leading-relaxed text-surface-400">
        <p className="mb-1 font-medium text-surface-300">读图指南</p>
        <p>
          网格收敛的基本要求：随 h → 0 你应该看到测量值**单调**逼近 gold（或至少一条光滑曲线），
          且相邻两级之间的变化随 h 的某个幂次衰减（Richardson extrapolation 就是在测这个幂次）。
          如果测量值在粗网格处大幅震荡、或 "看起来收敛了但其实离 gold 还很远"——那是 scheme 精度问题，不是 mesh。
        </p>
      </section>
    </div>
  );
}

function ConvergenceSparkline({
  series,
  goldRef,
  tolPct,
  activeIdx,
}: {
  series: { idx: number; label: string; value: number | null | undefined; status: ContractStatus }[];
  goldRef: number | undefined;
  tolPct: number | undefined;
  activeIdx: number;
}) {
  const W = 600;
  const H = 180;
  const padX = 40;
  const padY = 20;

  const values = series
    .map((s) => s.value)
    .filter((v): v is number => v != null && Number.isFinite(v));
  if (goldRef == null || !Number.isFinite(goldRef) || values.length === 0) {
    return (
      <div className="h-[180px] rounded border border-surface-800 bg-surface-950/40 p-3 text-[11px] text-surface-500">
        等待后端数据…
      </div>
    );
  }
  const allVals = [...values, goldRef];
  if (tolPct != null) {
    allVals.push(goldRef * (1 + tolPct), goldRef * (1 - tolPct));
  }
  const yMin = Math.min(...allVals);
  const yMax = Math.max(...allVals);
  const yRange = yMax - yMin || Math.abs(goldRef) * 0.2 || 1;
  const yPad = yRange * 0.15;
  const yLo = yMin - yPad;
  const yHi = yMax + yPad;

  const xStep = series.length > 1 ? (W - 2 * padX) / (series.length - 1) : 0;
  const toX = (i: number) => padX + i * xStep;
  const toY = (v: number) => padY + (H - 2 * padY) * (1 - (v - yLo) / (yHi - yLo));

  const goldY = toY(goldRef);
  const upperY = tolPct != null ? toY(goldRef * (1 + tolPct)) : null;
  const lowerY = tolPct != null ? toY(goldRef * (1 - tolPct)) : null;

  const points = series
    .map((s) =>
      s.value == null || !Number.isFinite(s.value)
        ? null
        : `${toX(s.idx)},${toY(s.value)}`,
    )
    .filter((p): p is string => p != null)
    .join(" ");

  const statusColor: Record<ContractStatus, string> = {
    PASS: "#4ade80",
    HAZARD: "#fbbf24",
    FAIL: "#f87171",
    UNKNOWN: "#9ca3af",
  };

  return (
    <div className="rounded border border-surface-800 bg-surface-950/40 p-3">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img">
        {/* tolerance band */}
        {upperY != null && lowerY != null && (
          <rect
            x={padX - 6}
            y={Math.min(upperY, lowerY)}
            width={W - 2 * padX + 12}
            height={Math.abs(upperY - lowerY)}
            fill="#4ade80"
            opacity={0.08}
          />
        )}
        {/* gold line */}
        <line
          x1={padX - 6}
          x2={W - padX + 6}
          y1={goldY}
          y2={goldY}
          stroke="#4ade80"
          strokeWidth={1.4}
          strokeDasharray="4 3"
        />
        <text x={W - padX + 10} y={goldY + 3} fontSize="10" fill="#4ade80">
          gold {formatNumber(goldRef)}
        </text>
        {/* connecting line */}
        <polyline
          points={points}
          fill="none"
          stroke="#60a5fa"
          strokeWidth={1.5}
          opacity={0.6}
        />
        {/* density anchor points */}
        {series.map((s) => {
          if (s.value == null || !Number.isFinite(s.value)) return null;
          const cx = toX(s.idx);
          const cy = toY(s.value);
          const r = s.idx === activeIdx ? 6 : 4;
          return (
            <g key={s.idx}>
              <circle
                cx={cx}
                cy={cy}
                r={r}
                fill={statusColor[s.status]}
                stroke="#0a0e14"
                strokeWidth={1.5}
              />
              <text
                x={cx}
                y={H - 4}
                textAnchor="middle"
                fontSize="10"
                fill={s.idx === activeIdx ? "#e5e7eb" : "#6b7280"}
              >
                {s.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

