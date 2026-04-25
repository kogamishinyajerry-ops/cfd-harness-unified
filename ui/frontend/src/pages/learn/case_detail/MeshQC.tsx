// MeshQC · Stage 3 MVP — red/yellow/green threshold band over mesh
// Richardson + GCI metrics, integrated into MeshTab below the existing
// grid-convergence sweep slider.
//
// Per Codex industrial-workbench meeting 2026-04-25 §3 + roadmap S3
// (workbench_rollout_roadmap.md). Source data:
// `/api/cases/{id}/mesh-metrics` which surfaces
// `ui.backend.services.grid_convergence.compute_gci_from_fixtures`.
//
// Codex meeting Lin/Sarah disagreement: metrics-pass ≠ physics-pass.
// We surface the case's contract_status separately (StoryTab) and keep
// MeshQC focused on the *numerical* convergence story so users don't
// conflate "GCI green" with "the case is correct".

import { useQuery } from "@tanstack/react-query";

import { api, ApiError } from "@/api/client";
import type { MeshMetrics, QcVerdict } from "@/types/mesh_metrics";

const COLOR: Record<QcVerdict, { bar: string; chip: string; text: string }> = {
  green: { bar: "#10b981", chip: "border-emerald-700/60 bg-emerald-950/40", text: "text-emerald-300" },
  yellow: { bar: "#f59e0b", chip: "border-amber-700/60 bg-amber-950/40", text: "text-amber-300" },
  red: { bar: "#ef4444", chip: "border-rose-700/60 bg-rose-950/40", text: "text-rose-300" },
  gray: { bar: "#475569", chip: "border-surface-700 bg-surface-900/40", text: "text-surface-400" },
};

const VERDICT_LABEL: Record<QcVerdict, string> = {
  green: "PASS",
  yellow: "MARGINAL",
  red: "FAIL",
  gray: "N/A",
};

export function MeshQC({ caseId }: { caseId: string }) {
  const { data, error, isLoading } = useQuery<MeshMetrics, ApiError>({
    queryKey: ["mesh-metrics", caseId],
    queryFn: () => api.getMeshMetrics(caseId),
    enabled: !!caseId,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="h-[200px] animate-pulse rounded-md border border-surface-800 bg-surface-900/40" />
    );
  }

  if (error?.status === 404) {
    return (
      <div className="rounded-md border border-surface-800 bg-surface-900/30 p-5 text-[12px] text-surface-500">
        Mesh QC band 暂未可用：该案例缺少 mesh_*_measurement.yaml fixture。
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-md border border-amber-700/60 bg-amber-950/30 p-4 text-[12px] text-amber-200">
        ⚠ mesh-metrics 加载失败：{error?.message ?? "unknown error"}
      </div>
    );
  }

  const gci = data.gci;
  const band = data.qc_band;

  return (
    <section className="rounded-md border border-surface-800 bg-surface-900/40 p-5">
      <div className="mb-4 flex items-baseline justify-between">
        <div>
          <h2 className="card-title">Mesh QC · 网格收敛信任带</h2>
          <p className="mt-1 text-[12px] text-surface-500">
            Richardson 外推 + GCI 不确定带 (Celik 2008) — 驱动 4 个色调验证条
          </p>
        </div>
        <span className="mono text-[10px] uppercase tracking-wider text-surface-600">
          mesh-metrics · v1
        </span>
      </div>

      {/* Data-source honesty badge — Opus 4.7 review 2026-04-25
          ACCEPT_WITH_COMMENTS: chip 数据来自合成 fixture (mesh_*_measurement.yaml)
          而非真实 checkMesh log。真值（skew / non-orthogonality / max-y+）待
          Stage 7 接入 docker-openfoam 真跑后才能填。这里用 amber 标签明示，
          避免新手把 GCI=green 误读为"网格通过 ANSYS-style mesh quality 检查"。 */}
      <div className="mb-4 inline-flex items-center gap-2 rounded-sm border border-amber-700/50 bg-amber-950/30 px-2.5 py-1 text-[11px] text-amber-200">
        <span className="mono text-[10px] uppercase tracking-wider text-amber-400">data source</span>
        <span>synthetic fixture (mesh_*_measurement.yaml)</span>
        <span className="text-surface-600">·</span>
        <span className="text-surface-400">真 skew / non-orthogonality / y+ 待 Stage 7</span>
      </div>

      {/* 4-bar QC band */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <QcChip
          label="Mesh 层数"
          value={`${data.densities.length} / 4`}
          verdict={band.n_levels}
          tooltip="≥4 = 完整 sweep，可计算 Richardson 外推；3 = 勉强够；<3 = 红"
        />
        <QcChip
          label="GCI₃₂ 不确定带"
          value={
            gci?.gci_32_pct != null
              ? `${gci.gci_32_pct.toFixed(2)}%`
              : "—"
          }
          verdict={band.gci_32}
          tooltip="Celik 2008 阈值：≤5% 绿；≤15% 黄；>15% 红"
        />
        <QcChip
          label="Richardson p_obs"
          value={
            gci?.p_obs != null ? gci.p_obs.toFixed(2) : "—"
          }
          verdict={band.richardson_p}
          tooltip="二阶离散方案理论 p≈2；绿 [1.5,2.5] / 黄 [1,4] / 红 越界或非定义"
        />
        <QcChip
          label="渐近范围"
          value={
            gci?.asymptotic_range_ok == null
              ? "—"
              : gci.asymptotic_range_ok
                ? "在范围内"
                : "未达"
          }
          verdict={band.asymptotic_range}
          tooltip="GCI₃₂·r^p ≈ GCI₂₁ 在 25% 内 → sweep 已进入渐近域，外推可信"
        />
      </div>

      {/* Density ladder + GCI summary */}
      <div className="mt-5 grid gap-4 md:grid-cols-[1fr_280px]">
        <DensityLadder data={data} />
        <RichardsonSummary gci={gci} />
      </div>

      {data.diagnostic_note && (
        <p className="mt-3 rounded-sm border border-surface-800 bg-surface-950 p-2 text-[11px] text-surface-400">
          <span className="mono text-surface-500">note:</span> {data.diagnostic_note}
        </p>
      )}
      {gci?.note && gci.note !== "ok" && (
        <p className="mt-2 rounded-sm border border-amber-700/40 bg-amber-950/20 p-2 text-[11px] text-amber-200">
          <span className="mono">richardson:</span> {gci.note}
        </p>
      )}

      {/* Codex disagreement guard: metrics-pass ≠ physics-pass */}
      <p className="mt-4 border-t border-surface-800 pt-3 text-[11px] leading-relaxed text-surface-500">
        <strong className="text-surface-400">读图守则：</strong>
        Mesh QC 全绿 ≠ 案例物理对。它只说明数值收敛性可信。物理对错由 Story tab
        的 contract_status 与 Compare tab 的 gold 偏差判定。
      </p>
    </section>
  );
}

// --- Chip ----------------------------------------------------------------

function QcChip({
  label,
  value,
  verdict,
  tooltip,
}: {
  label: string;
  value: string;
  verdict: QcVerdict;
  tooltip?: string;
}) {
  const c = COLOR[verdict];
  return (
    <div
      className={`rounded-md border px-3 py-2 ${c.chip}`}
      title={tooltip}
    >
      <div className="flex items-center justify-between text-[10px] uppercase tracking-wider text-surface-500">
        <span>{label}</span>
        <span className={c.text}>{VERDICT_LABEL[verdict]}</span>
      </div>
      <p className={`mono mt-1 text-lg font-semibold ${c.text}`}>{value}</p>
      {/* mini bar */}
      <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-surface-950">
        <div
          className="h-full"
          style={{
            backgroundColor: c.bar,
            width:
              verdict === "green"
                ? "100%"
                : verdict === "yellow"
                  ? "60%"
                  : verdict === "red"
                    ? "30%"
                    : "10%",
          }}
        />
      </div>
    </div>
  );
}

// --- Density ladder ------------------------------------------------------
// Bar chart of |value − f_extrapolated| per density. Visualizes how each
// finer mesh tightens around the Richardson estimate.

function DensityLadder({ data }: { data: MeshMetrics }) {
  const fExt = data.gci?.f_extrapolated;
  const dens = data.densities;
  const W = 320;
  const H = 110;
  const padL = 56;
  const padR = 12;
  const padT = 12;
  const padB = 22;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  // Compute |dev| per density vs Richardson extrapolation if available;
  // otherwise vs the finest mesh value.
  const reference = fExt ?? (dens.at(-1)?.value ?? 0);
  const devs = dens.map((d) =>
    d.value == null ? null : Math.abs(d.value - (reference ?? 0)),
  );
  const validDevs = devs.filter((v): v is number => v != null && Number.isFinite(v));
  const maxDev = Math.max(...validDevs, 1e-9);

  return (
    <div className="rounded-md border border-surface-800 bg-surface-950/40 p-3">
      <p className="mb-2 text-[11px] uppercase tracking-wider text-surface-500">
        密度阶梯 · |value − f_∞|
      </p>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" aria-hidden>
        {/* x-axis */}
        <line
          x1={padL}
          y1={H - padB}
          x2={W - padR}
          y2={H - padB}
          stroke="#334155"
          strokeWidth="0.5"
        />
        {/* per-density bars */}
        {dens.map((d, i) => {
          const dev = devs[i];
          const barW = (innerW / dens.length) * 0.6;
          const barX = padL + (innerW / dens.length) * (i + 0.2);
          const ratio = dev != null ? dev / maxDev : 0;
          const barH = innerH * ratio;
          return (
            <g key={d.id}>
              <rect
                x={barX}
                y={H - padB - barH}
                width={barW}
                height={Math.max(barH, 1)}
                fill="#0ea5e9"
                opacity={0.85}
              />
              <text
                x={barX + barW / 2}
                y={H - padB + 12}
                fontSize="9"
                textAnchor="middle"
                fill="#94a3b8"
                className="mono"
              >
                {d.n_cells_1d}
              </text>
              {dev != null && Number.isFinite(dev) && (
                <text
                  x={barX + barW / 2}
                  y={H - padB - barH - 3}
                  fontSize="8"
                  textAnchor="middle"
                  fill="#cbd5e1"
                  className="mono"
                >
                  {dev < 0.001 ? dev.toExponential(1) : dev.toFixed(3)}
                </text>
              )}
            </g>
          );
        })}
        <text
          x={6}
          y={padT + 8}
          fontSize="9"
          fill="#64748b"
          className="mono"
        >
          {fExt != null
            ? `f_∞ ≈ ${formatNum(fExt)}`
            : "f_∞ unavailable"}
        </text>
        <text
          x={6}
          y={H - padB + 12}
          fontSize="9"
          fill="#64748b"
          className="mono"
        >
          n_1D
        </text>
      </svg>
    </div>
  );
}

// --- Richardson summary --------------------------------------------------

function RichardsonSummary({ gci }: { gci: MeshMetrics["gci"] }) {
  if (!gci) {
    return (
      <div className="rounded-md border border-surface-800 bg-surface-950/40 p-4 text-[11px] text-surface-500">
        无 Richardson 输出（密度阶梯不足 3 级）
      </div>
    );
  }
  return (
    <div className="rounded-md border border-surface-800 bg-surface-950/40 p-4 text-[11px]">
      <p className="mb-2 text-[10px] uppercase tracking-wider text-surface-500">
        Richardson 外推
      </p>
      <Row label="f_∞" value={gci.f_extrapolated != null ? formatNum(gci.f_extrapolated) : "—"} />
      <Row
        label="ε₂₁ (粗→中)"
        value={gci.e_21 != null ? `${gci.e_21.toFixed(2)}%` : "—"}
      />
      <Row
        label="ε₃₂ (中→细)"
        value={gci.e_32 != null ? `${gci.e_32.toFixed(2)}%` : "—"}
      />
      <Row
        label="GCI₂₁"
        value={gci.gci_21_pct != null ? `${gci.gci_21_pct.toFixed(2)}%` : "—"}
      />
      <Row
        label="GCI₃₂"
        value={gci.gci_32_pct != null ? `${gci.gci_32_pct.toFixed(2)}%` : "—"}
        bold
      />
    </div>
  );
}

function Row({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <div className="flex items-baseline justify-between border-b border-surface-900 py-0.5">
      <span className="text-surface-500">{label}</span>
      <span className={`mono ${bold ? "text-surface-100" : "text-surface-300"}`}>
        {value}
      </span>
    </div>
  );
}

function formatNum(v: number): string {
  if (!Number.isFinite(v)) return String(v);
  const abs = Math.abs(v);
  if (abs === 0) return "0";
  if (abs >= 1000 || abs < 0.001) return v.toExponential(2);
  return Number(v.toPrecision(4)).toString();
}
