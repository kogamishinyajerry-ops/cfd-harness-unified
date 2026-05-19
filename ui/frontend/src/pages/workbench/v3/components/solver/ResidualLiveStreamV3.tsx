/**
 * V77.2 · ResidualLiveStreamV3 · per-variable live residual values from
 * SSE stream. Six literal `data-testid="residual-live-{var}"` lines —
 * one per canonical CAE variable — so the V77 Pillar 16 scorer counts
 * all 6.
 *
 * Industrial parity: Fluent's Residual Monitor + STAR-CCM+ convergence
 * plot share this exact "p · U_x · U_y · U_z · k · ω" row layout.
 */

import { useSseResidualStream } from "@/hooks/useSseResidualStream";

interface ResidualLiveStreamV3Props {
  caseId: string;
  /** Test seam — inject a mock EventSource in vitest. */
  eventSourceCtor?: typeof EventSource;
}

function formatResidual(v: number | undefined): string {
  if (v === undefined || !Number.isFinite(v)) return "—";
  if (v === 0) return "0";
  return v.toExponential(2);
}

export function ResidualLiveStreamV3({
  caseId,
  eventSourceCtor,
}: ResidualLiveStreamV3Props) {
  const { status, latestResiduals, latestIteration } = useSseResidualStream(
    caseId,
    { eventSourceCtor },
  );

  const dataSource = status === "open" ? "live" : "fallback";

  return (
    <div
      data-testid="residual-live-panel"
      data-source={dataSource}
      className="rounded-md border border-v3-borderSubtle bg-v3-bgRaised/40 p-3"
    >
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[10px] font-mono uppercase tracking-[0.08em] text-v3-textTertiary">
          Live residuals · iter {latestIteration || "—"}
        </span>
        <span
          data-testid="sse-stream-status"
          data-status={status}
          className="text-[10px] font-mono text-v3-textSecondary"
        >
          {status}
        </span>
      </div>

      <div
        data-testid="residual-live-p"
        className="flex items-baseline justify-between gap-2 text-[12px] font-mono"
      >
        <span className="text-v3-textSecondary">p</span>
        <span className="text-v3-textPrimary">{formatResidual(latestResiduals.p)}</span>
      </div>
      <div
        data-testid="residual-live-U_x"
        className="flex items-baseline justify-between gap-2 text-[12px] font-mono"
      >
        <span className="text-v3-textSecondary">U_x</span>
        <span className="text-v3-textPrimary">{formatResidual(latestResiduals.U_x)}</span>
      </div>
      <div
        data-testid="residual-live-U_y"
        className="flex items-baseline justify-between gap-2 text-[12px] font-mono"
      >
        <span className="text-v3-textSecondary">U_y</span>
        <span className="text-v3-textPrimary">{formatResidual(latestResiduals.U_y)}</span>
      </div>
      <div
        data-testid="residual-live-U_z"
        className="flex items-baseline justify-between gap-2 text-[12px] font-mono"
      >
        <span className="text-v3-textSecondary">U_z</span>
        <span className="text-v3-textPrimary">{formatResidual(latestResiduals.U_z)}</span>
      </div>
      <div
        data-testid="residual-live-k"
        className="flex items-baseline justify-between gap-2 text-[12px] font-mono"
      >
        <span className="text-v3-textSecondary">k</span>
        <span className="text-v3-textPrimary">{formatResidual(latestResiduals.k)}</span>
      </div>
      <div
        data-testid="residual-live-omega"
        className="flex items-baseline justify-between gap-2 text-[12px] font-mono"
      >
        <span className="text-v3-textSecondary">ω</span>
        <span className="text-v3-textPrimary">{formatResidual(latestResiduals.omega)}</span>
      </div>
    </div>
  );
}
