// Advanced tab: decision trail, raw YAML, link to /audit-package and
// /pro evidence surfaces. Power-user pivot from /learn into /pro.
//
// Extracted 2026-04-25 from LearnCaseDetailPage.tsx (Stage 1 shell-split,
// per Codex industrial-workbench meeting verdict). Behavior unchanged.

import { Link } from "react-router-dom";

import type { ValidationReport } from "@/types/validation";


export function AdvancedTab({
  caseId,
  report,
}: {
  caseId: string;
  report: ValidationReport | undefined;
}) {
  return (
    <div className="space-y-6">
      <div className="rounded-md border border-surface-800 bg-surface-900/40 p-5">
        <p className="card-title mb-2">为什么这里叫 Advanced</p>
        <p className="text-[13px] leading-relaxed text-surface-300">
          下面这些能力——决策溯源、签名审计包、字节可复现打包——
          是给要对审计员、合规官、审稿人负责的专业用户准备的。
          学习场景用不到也没关系。等你真的要把一个 CFD 预测交给别人信的时候再回来。
        </p>
      </div>

      {/* Decisions trail — compact */}
      <section className="rounded-md border border-surface-800 bg-surface-900/30 p-5">
        <h3 className="card-title mb-3">决策溯源 · Decision trail</h3>
        {report && report.decisions_trail.length > 0 ? (
          <ul className="space-y-2">
            {report.decisions_trail.map((d) => (
              <li key={d.decision_id} className="flex items-start gap-3 text-[13px]">
                <span className="mono mt-0.5 inline-flex shrink-0 rounded-sm bg-surface-800 px-1.5 py-0.5 text-[11px] text-surface-200">
                  {d.decision_id}
                </span>
                <span className="text-surface-300">{d.title}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-[12px] text-surface-500">
            这个案例还没有关联决策。复杂案例（比如 DHC、duct_flow）会累积决策轨迹。
          </p>
        )}
      </section>

      {/* Audit concerns — if any */}
      {report && report.audit_concerns.length > 0 && (
        <section className="rounded-md border border-surface-800 bg-surface-900/30 p-5">
          <h3 className="card-title mb-3">审计关注项</h3>
          <ul className="space-y-3">
            {report.audit_concerns.map((ac, i) => (
              <li key={i} className="text-[13px]">
                <div className="mb-1 flex items-center gap-2">
                  <span className="mono inline-flex rounded-sm bg-amber-950/40 px-1.5 py-0.5 text-[10px] text-amber-200">
                    {ac.concern_type}
                  </span>
                </div>
                <p className="leading-relaxed text-surface-300">{ac.summary}</p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Bridge to Pro Workbench */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-sky-900/40 bg-sky-950/15 px-5 py-4">
        <div>
          <p className="text-[13px] text-surface-200">
            要生成签名的证据包（manifest + zip + HMAC .sig）？
          </p>
          <p className="mt-1 text-[11px] text-surface-400">
            Pro Workbench · Audit Package Builder ·{" "}
            <span className="mono">case_id={caseId}</span>
          </p>
        </div>
        <Link
          to="/audit-package"
          className="rounded-md bg-sky-600 px-3.5 py-1.5 text-[13px] font-medium text-white hover:bg-sky-500"
        >
          进入 Audit Package Builder →
        </Link>
      </div>
    </div>
  );
}

// --- Shared callouts ----------------------------------------------------------

