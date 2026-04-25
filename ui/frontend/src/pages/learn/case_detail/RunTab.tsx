// Run tab: solver invocation + residuals preview. The lightweight
// "kick off solver from /learn" surface. Live streaming lives in
// /pro Run Monitor; here we just show recent residuals snapshot.
//
// Extracted 2026-04-25 from LearnCaseDetailPage.tsx (Stage 1 shell-split,
// per Codex industrial-workbench meeting verdict). Behavior unchanged.

import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

// --- Run tab body ------------------------------------------------------

export function RunTab({ caseId }: { caseId: string }) {
  return (
    <div className="space-y-6">
      <div className="rounded-md border border-surface-800 bg-surface-900/40 p-5">
        <p className="card-title mb-3">运行求解器</p>
        <p className="text-[13px] leading-relaxed text-surface-300">
          真正的 solver 执行、残差流式、收敛监测在 Pro Workbench 里。
          这里我们保持学习视角——先理解问题，再动手。
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Link
            to={`/runs/${caseId}`}
            className="rounded-md bg-sky-600 px-3.5 py-1.5 text-[13px] font-medium text-white hover:bg-sky-500"
          >
            去 Pro Workbench 跑这个案例 →
          </Link>
          <Link
            to={`/cases/${caseId}/edit`}
            className="rounded-md border border-surface-700 bg-surface-900 px-3.5 py-1.5 text-[13px] text-surface-200 hover:border-surface-600"
          >
            查看/编辑 YAML
          </Link>
        </div>
      </div>

      {/* DEC-V61-047 round-1 F2 blocker fix: the synthetic SVG preview
          below was previously shown under "你大概会看到" with no clear
          signal that it was decorative. A novice reading the page
          could mistake it for this case's real solver trace. We now
          try the real audit_real_run residuals.png first (exists for
          all 10 cases via phase5_audit_run.py captures), and only
          fall back to the synthetic preview with an explicit 示意图
          marker if the real artifact is missing. */}
      <RunResidualsCard caseId={caseId} />
    </div>
  );
}

function RunResidualsCard({ caseId }: { caseId: string }) {
  const realUrl = `/api/cases/${encodeURIComponent(caseId)}/runs/audit_real_run/renders/residuals.png`;
  const [realOk, setRealOk] = useState<boolean | null>(null);

  return (
    <div className="rounded-md border border-surface-800 bg-surface-900/30 p-5">
      <div className="mb-3 flex items-baseline justify-between">
        <p className="card-title">残差收敛 · 真实 solver 输出</p>
        {realOk && (
          <span className="mono text-[10px] text-contract-pass">
            audit_real_run · 真实数据
          </span>
        )}
      </div>
      {realOk !== false ? (
        <div className="rounded-md border border-surface-800 bg-white p-2">
          <img
            src={realUrl}
            alt={`${caseId} audit_real_run residuals`}
            className="w-full"
            onLoad={() => setRealOk(true)}
            onError={() => setRealOk(false)}
          />
        </div>
      ) : (
        <>
          <div className="mb-2 rounded-md border border-amber-600/50 bg-amber-950/30 p-2 text-[11px] text-amber-200">
            <span className="font-semibold">⚠ 示意图 · illustrative only</span>
            ：该 case 的 audit_real_run 真实残差 PNG 暂未生成（可能是尚未 phase-5
            audit 过）。下方 SVG 是<strong>示意性装饰</strong>，不是本 case 真实
            的 solver 残差 —— 目的仅是让新手了解"残差应该长什么样"。要看真实残差
            请去 Pro Workbench 或重跑 <code className="mono">scripts/phase5_audit_run.py</code>。
          </div>
          <ResidualsPreview />
        </>
      )}
      <p className="mt-4 text-[12px] leading-relaxed text-surface-400">
        残差随迭代步数下降到判据以下意味着解收敛——但<strong>收敛不等于"算对"</strong>。
        残差降下去只说明离散方程的数值解稳定了，它不知道你的 mesh / BC /
        model 是否符合物理。下一步请回到 "对比" tab 看数值能不能贴住黄金标准。
      </p>
    </div>
  );
}

// Pure-SVG residual chart (no chart lib dependency). Shows a decaying
// multi-residual hint like a real simpleFoam log would render.
function ResidualsPreview() {
  const SERIES = useMemo(() => {
    const makeSeries = (decay: number, noise: number, seed: number) => {
      const pts: [number, number][] = [];
      let val = 1;
      for (let i = 0; i <= 60; i++) {
        val *= decay;
        const jitter = Math.sin(i * 0.7 + seed) * noise * val;
        pts.push([i, Math.max(val + jitter, 1e-6)]);
      }
      return pts;
    };
    return [
      { key: "p", color: "#60a5fa", pts: makeSeries(0.9, 0.2, 0.1) },
      { key: "Ux", color: "#a78bfa", pts: makeSeries(0.91, 0.22, 1.3) },
      { key: "Uy", color: "#f472b6", pts: makeSeries(0.92, 0.18, 2.1) },
    ];
  }, []);

  const W = 560;
  const H = 160;
  const PADL = 36;
  const PADR = 12;
  const PADT = 8;
  const PADB = 22;

  const xToPx = (x: number) => PADL + (x / 60) * (W - PADL - PADR);
  const yToPx = (y: number) => {
    // log scale from 1 down to 1e-6
    const logY = Math.log10(Math.max(y, 1e-6));
    const frac = (0 - logY) / 6; // 0 at top, 1 at bottom
    return PADT + frac * (H - PADT - PADB);
  };

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" aria-hidden>
      {/* log-grid horizontal lines at 1e0..1e-6 */}
      {[0, -1, -2, -3, -4, -5, -6].map((p) => (
        <g key={p}>
          <line
            x1={PADL}
            x2={W - PADR}
            y1={yToPx(Math.pow(10, p))}
            y2={yToPx(Math.pow(10, p))}
            stroke="currentColor"
            className="text-surface-800"
            strokeWidth="0.5"
          />
          <text
            x={PADL - 6}
            y={yToPx(Math.pow(10, p)) + 3}
            fontSize="10"
            textAnchor="end"
            fill="currentColor"
            className="mono text-surface-500"
          >
            1e{p}
          </text>
        </g>
      ))}
      {/* x-axis */}
      <line
        x1={PADL}
        x2={W - PADR}
        y1={H - PADB}
        y2={H - PADB}
        stroke="currentColor"
        className="text-surface-700"
        strokeWidth="1"
      />
      <text
        x={(W + PADL) / 2}
        y={H - 6}
        fontSize="10"
        textAnchor="middle"
        fill="currentColor"
        className="text-surface-500"
      >
        迭代步数
      </text>
      {/* series */}
      {SERIES.map((s) => (
        <g key={s.key}>
          <polyline
            fill="none"
            stroke={s.color}
            strokeWidth="1.4"
            points={s.pts.map(([x, y]) => `${xToPx(x)},${yToPx(y)}`).join(" ")}
            opacity="0.85"
          />
          <text
            x={xToPx(61)}
            y={yToPx(s.pts[s.pts.length - 1][1]) + 3}
            fontSize="10"
            fill={s.color}
            className="mono"
          >
            {s.key}
          </text>
        </g>
      ))}
    </svg>
  );
}

// --- Advanced tab -------------------------------------------------------------

