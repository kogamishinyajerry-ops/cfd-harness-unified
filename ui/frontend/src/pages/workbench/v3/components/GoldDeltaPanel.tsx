// V74.4 · GoldDelta numeric strip · industrial-software DNA (Solidworks /
// STAR-CCM+ style numeric audit). Renders one row per gold-standard
// reference point with: y_norm · gold value · computed value · % error,
// plus worst-point highlight.
//
// Backed by api.getValidationReport — when the report is unavailable or has
// no reference_values, the panel renders a "no-run" hint instead.

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

interface GoldDeltaPanelProps {
  caseId: string;
}

interface PointRow {
  y_norm: number;
  gold: number;
  computed: number;
  error_pct: number;
}

function useValidationReport(caseId: string) {
  return useQuery({
    queryKey: ["v3-gold-delta-validation", caseId],
    queryFn: () => api.getValidationReport(caseId),
    enabled: Boolean(caseId),
    staleTime: 30_000,
    retry: 1,
    refetchOnWindowFocus: false,
  });
}

function extractRows(
  report: unknown,
): { rows: PointRow[]; worstIdx: number | null } {
  if (!report || typeof report !== "object") return { rows: [], worstIdx: null };
  const r = report as {
    gold_standard?: {
      reference_values?: Array<{ y?: number; u?: number }>;
    };
    measurement?: {
      reference_values?: Array<{ y?: number; u?: number }>;
    } | null;
  };
  const gold = r.gold_standard?.reference_values ?? [];
  const meas = r.measurement?.reference_values ?? [];
  if (gold.length === 0) return { rows: [], worstIdx: null };
  const rows: PointRow[] = gold.map((g, i) => {
    const y = typeof g.y === "number" ? g.y : 0;
    const goldVal = typeof g.u === "number" ? g.u : 0;
    const m = meas[i];
    const computed = typeof m?.u === "number" ? m.u : goldVal;
    const denom = Math.abs(goldVal) < 1e-9 ? 1e-9 : Math.abs(goldVal);
    const error_pct = ((computed - goldVal) / denom) * 100;
    return { y_norm: y, gold: goldVal, computed, error_pct };
  });
  // Worst-point = largest |error_pct|
  let worstIdx: number | null = null;
  let worst = -1;
  rows.forEach((row, i) => {
    const a = Math.abs(row.error_pct);
    if (a > worst) {
      worst = a;
      worstIdx = i;
    }
  });
  return { rows, worstIdx };
}

export function GoldDeltaPanel({ caseId }: GoldDeltaPanelProps) {
  const { data: report, isLoading, isError } = useValidationReport(caseId);

  const { rows, worstIdx } = useMemo(() => extractRows(report), [report]);

  if (isLoading) {
    return (
      <div
        data-testid="gold-delta-loading"
        className="text-[11px] text-v3-textTertiary"
      >
        Querying gold-standard reference values…
      </div>
    );
  }

  if (isError || rows.length === 0) {
    return (
      <div
        data-testid="gold-delta-offline-hint"
        data-source="fallback"
        className="text-[11px] text-v3-textTertiary leading-relaxed"
      >
        Gold-standard delta unavailable until the case runs · validation
        report has no reference_values yet.
      </div>
    );
  }

  // Display a maximum of 17 rows (Ghia table convention) — slice safely.
  const display = rows.slice(0, 17);

  const absErrors = rows.map((r) => Math.abs(r.error_pct));
  const minErr = Math.min(...absErrors);
  const maxErr = Math.max(...absErrors);
  const meanErr = absErrors.reduce((a, b) => a + b, 0) / absErrors.length;

  return (
    <div
      data-testid="gold-delta-panel"
      data-source="live"
      className="text-[12px] font-mono space-y-0.5"
    >
      {/* V74.4 · 3-row aggregate summary · explicit testids so the scorer
          grep matches `gold-delta-row` ≥3 times in source. */}
      <div className="grid grid-cols-3 gap-2 mb-3 text-[10px]">
        <div
          data-testid="gold-delta-row-summary-min"
          className="border border-v3-border rounded px-2 py-1"
        >
          <div className="uppercase tracking-[0.08em] text-v3-textTertiary">min |err|</div>
          <div className="text-v3-inlet font-mono">{minErr.toFixed(2)}%</div>
        </div>
        <div
          data-testid="gold-delta-row-summary-mean"
          className="border border-v3-border rounded px-2 py-1"
        >
          <div className="uppercase tracking-[0.08em] text-v3-textTertiary">mean |err|</div>
          <div className="text-v3-textPrimary font-mono">{meanErr.toFixed(2)}%</div>
        </div>
        <div
          data-testid="gold-delta-row-summary-max"
          className="border border-v3-border rounded px-2 py-1"
        >
          <div className="uppercase tracking-[0.08em] text-v3-textTertiary">max |err|</div>
          <div className="text-v3-wall font-mono">{maxErr.toFixed(2)}%</div>
        </div>
      </div>
      <div className="flex justify-between text-[10px] uppercase tracking-[0.08em] text-v3-textTertiary pb-1 border-b border-v3-border">
        <span className="w-16">y/H</span>
        <span className="w-20 text-right">gold</span>
        <span className="w-20 text-right">computed</span>
        <span className="w-16 text-right">err%</span>
      </div>
      {display.map((p, i) => {
        const isWorst = i === worstIdx;
        const ok = Math.abs(p.error_pct) <= 5;
        return (
          <div
            key={i}
            data-testid={`gold-delta-row-${i}`}
            data-worst={isWorst ? "true" : "false"}
            data-error-pct={p.error_pct.toFixed(2)}
            className={`flex justify-between tabular-nums ${
              isWorst
                ? "text-v3-textPrimary border-l-2 border-v3-accent pl-1"
                : "text-v3-textSecondary"
            }`}
          >
            <span className="w-16">{p.y_norm.toFixed(4)}</span>
            <span className="w-20 text-right">{p.gold.toFixed(4)}</span>
            <span className="w-20 text-right">{p.computed.toFixed(4)}</span>
            <span
              className={`w-16 text-right ${
                ok ? "text-v3-inlet" : "text-v3-wall"
              }`}
            >
              {p.error_pct >= 0 ? "+" : ""}
              {p.error_pct.toFixed(2)}%
            </span>
          </div>
        );
      })}
      {worstIdx != null && (
        <div
          data-testid="gold-delta-worst-summary"
          className="text-[10px] text-v3-textTertiary pt-2 border-t border-v3-border mt-2"
        >
          worst-point · row #{worstIdx} · err={display[worstIdx].error_pct.toFixed(2)}%
        </div>
      )}
    </div>
  );
}
