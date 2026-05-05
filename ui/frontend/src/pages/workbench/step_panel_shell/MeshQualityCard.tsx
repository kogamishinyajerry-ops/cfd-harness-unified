// DEC-V61-127 · Mesh-quality card · Fluent-style gauges + per-patch chips.
//
// Mounts under Step2Mesh's mesh-success card after a mesh has been
// generated. Fetches GET /api/cases/{id}/mesh-quality?run_checkmesh=true,
// renders threshold-colored horizontal gauges for skewness /
// non-orthogonality / aspect ratio + a verdict pill + per-patch face
// counts. Graceful degradation: when V126 returns the base V122 shape
// (container unavailable or run_checkmesh skipped), the gauge area
// shows "checkMesh skipped" instead of zeros.
//
// Threshold bands match published CFD industry conventions, NOT a
// Fluent-specific copyrighted scale:
//   * Skewness: 0.5 (info) / 0.7 (warning) / 0.95 (Fluent reject)
//   * Non-orthogonality (deg): 45 / 65 / 75 (OpenFOAM corrector limit)
//   * Aspect ratio: 10 / 100 / 1000
// Color in 4 zones (green / amber / orange / rose) matches the rest of
// the workbench's status palette.

import { useEffect, useState } from "react";

import { api, ApiError } from "@/api/client";
import type {
  MeshQualityReport,
  MeshQualitySeverity,
} from "./types";

interface MeshQualityCardProps {
  caseId: string;
  /** Bumped by the parent each time Step2Mesh successfully regenerates
   *  the mesh, so the card re-fetches against the new polyMesh. */
  meshGenSeq: number;
}

type LoadState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; report: MeshQualityReport }
  | { status: "error"; message: string };

// ────────── Threshold bands ──────────

interface GaugeBand {
  /** Upper bound (inclusive). null = open-ended (the "red" cap). */
  max: number | null;
  /** Tailwind tint name keyed in the band swatch table below. */
  tone: "green" | "amber" | "orange" | "rose";
  label: string;
}

const SKEWNESS_BANDS: GaugeBand[] = [
  { max: 0.5, tone: "green", label: "good" },
  { max: 0.7, tone: "amber", label: "marginal" },
  { max: 0.95, tone: "orange", label: "warning" },
  { max: null, tone: "rose", label: "reject" },
];
const SKEWNESS_AXIS_MAX = 1.0;

const NON_ORTHO_BANDS: GaugeBand[] = [
  { max: 45, tone: "green", label: "good" },
  { max: 65, tone: "amber", label: "marginal" },
  { max: 75, tone: "orange", label: "warning" },
  { max: null, tone: "rose", label: "reject" },
];
const NON_ORTHO_AXIS_MAX = 90;

const ASPECT_RATIO_BANDS: GaugeBand[] = [
  { max: 10, tone: "green", label: "good" },
  { max: 100, tone: "amber", label: "marginal" },
  { max: 1000, tone: "orange", label: "warning" },
  { max: null, tone: "rose", label: "reject" },
];
// Aspect ratio uses log scale visually; clamp display at 1e4.
const ASPECT_RATIO_AXIS_MAX = 1e4;

const TONE_BG: Record<GaugeBand["tone"], string> = {
  green: "bg-emerald-500/30",
  amber: "bg-amber-500/30",
  orange: "bg-orange-500/30",
  rose: "bg-rose-500/40",
};
const TONE_TEXT: Record<GaugeBand["tone"], string> = {
  green: "text-emerald-300",
  amber: "text-amber-300",
  orange: "text-orange-300",
  rose: "text-rose-300",
};
const TONE_BORDER: Record<GaugeBand["tone"], string> = {
  green: "border-emerald-500/40",
  amber: "border-amber-500/40",
  orange: "border-orange-500/40",
  rose: "border-rose-500/40",
};

function classifyValue(value: number, bands: GaugeBand[]): GaugeBand {
  for (const band of bands) {
    if (band.max === null || value <= band.max) return band;
  }
  return bands[bands.length - 1];
}

type AxisScale = "linear" | "log";

/** Map a value to a 0-100 percentage along the gauge bar.
 *
 * R1 P2 fix: aspect-ratio bands span 10 / 100 / 1000 / 10000 — on a
 * linear axis those bands occupy 0.1 / 0.9 / 9 / 90 percent, bunching
 * normal values against the left edge. Log scale (`log10(value+1)` /
 * `log10(axisMax+1)`) gives each decade equal width, matching how
 * engineers reason about aspect ratio. Linear stays the default for
 * skewness (0..1) and non-orthogonality (0..90) where the bands are
 * already evenly distributed.
 */
function clampPercent(
  value: number,
  axisMax: number,
  scale: AxisScale = "linear",
): number {
  if (!isFinite(value) || value <= 0) return 0;
  if (value >= axisMax) return 100;
  if (scale === "log") {
    return (Math.log10(value + 1) / Math.log10(axisMax + 1)) * 100;
  }
  return (value / axisMax) * 100;
}

// ────────── Sub-components ──────────

function VerdictPill({
  report,
}: {
  report: MeshQualityReport;
}) {
  // V126 path: explicit Mesh OK / failed verdict.
  if (report.report_kind === "v126" && report.checkmesh_mesh_ok !== null) {
    if (report.checkmesh_mesh_ok) {
      return (
        <span className="rounded-sm border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 font-mono text-[11px] text-emerald-300">
          Mesh OK
        </span>
      );
    }
    const n = report.checkmesh_failed_checks?.length ?? 0;
    return (
      <span className="rounded-sm border border-rose-500/40 bg-rose-500/15 px-2 py-0.5 font-mono text-[11px] text-rose-200">
        Failed {n} check{n === 1 ? "" : "s"}
      </span>
    );
  }
  // V122 fallback or V126 with checkmesh skipped.
  const hasCritical = report.warnings.some((w) => w.severity === "critical");
  const hasWarning = report.warnings.some((w) => w.severity === "warning");
  if (hasCritical) {
    return (
      <span className="rounded-sm border border-rose-500/40 bg-rose-500/15 px-2 py-0.5 font-mono text-[11px] text-rose-200">
        Critical issues
      </span>
    );
  }
  if (hasWarning) {
    return (
      <span className="rounded-sm border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 font-mono text-[11px] text-amber-200">
        Has warnings
      </span>
    );
  }
  return (
    <span className="rounded-sm border border-surface-700 bg-surface-800 px-2 py-0.5 font-mono text-[11px] text-surface-300">
      checkMesh skipped
    </span>
  );
}

interface QualityGaugeProps {
  label: string;
  value: number | null;
  bands: GaugeBand[];
  axisMax: number;
  /** Optional formatter for the displayed value (e.g. "65°", "0.42"). */
  format?: (v: number) => string;
  /** R1 P2: aspect ratio uses log10 scale so each decade gets equal
   *  bar width. Default is linear for skewness / non-orthogonality. */
  scale?: AxisScale;
}

function QualityGauge({
  label,
  value,
  bands,
  axisMax,
  format,
  scale = "linear",
}: QualityGaugeProps) {
  // Render the band ladder as a stacked horizontal bar with a needle
  // overlay at the current value. When value is null (skipped), render
  // the band ladder dimmed with no needle so the reader still sees the
  // threshold geography.
  const skipped = value === null;
  const band = !skipped ? classifyValue(value, bands) : null;
  const needlePercent = !skipped ? clampPercent(value, axisMax, scale) : 0;
  return (
    <div data-testid={`mesh-quality-gauge-${label.replace(/\s+/g, "-").toLowerCase()}`}>
      <div className="flex items-baseline justify-between text-[11px]">
        <span className="text-surface-400">{label}</span>
        <span
          className={`font-mono ${
            skipped ? "text-surface-600" : band ? TONE_TEXT[band.tone] : ""
          }`}
        >
          {skipped
            ? "skipped"
            : format
              ? format(value)
              : value.toFixed(2)}
          {!skipped && band ? ` · ${band.label}` : ""}
        </span>
      </div>
      <div
        className={`relative mt-1 flex h-2 overflow-hidden rounded-sm ${
          skipped ? "opacity-40" : ""
        }`}
        role="img"
        aria-label={
          skipped
            ? `${label}: skipped`
            : `${label}: ${(format ? format(value) : value.toFixed(2))} (${band?.label ?? ""})`
        }
      >
        {bands.map((b, i) => {
          // Each band's width matches the SAME scale the needle uses
          // (linear or log10), so the band geography on the bar is
          // visually consistent with where the needle lands. R1 P2
          // closure: previously linear-only width math collapsed the
          // 10/100/1000 aspect-ratio bands to <10% combined.
          const prevMax = i === 0 ? 0 : (bands[i - 1].max ?? axisMax);
          const cap = b.max === null ? axisMax : Math.min(b.max, axisMax);
          const startPct = clampPercent(prevMax, axisMax, scale);
          const endPct = clampPercent(cap, axisMax, scale);
          const widthPct = endPct - startPct;
          if (widthPct <= 0) return null;
          return (
            <div
              key={`${label}-${b.label}-${i}`}
              className={TONE_BG[b.tone]}
              style={{ width: `${widthPct}%` }}
              title={`${b.label}${b.max !== null ? ` ≤ ${b.max}` : ""}`}
            />
          );
        })}
        {!skipped && (
          <div
            className="absolute top-0 h-2 w-0.5 bg-surface-50"
            style={{ left: `${needlePercent}%` }}
            aria-hidden="true"
          />
        )}
      </div>
    </div>
  );
}

function PatchChips({
  patchFaceCounts,
}: {
  patchFaceCounts: Record<string, number>;
}) {
  const entries = Object.entries(patchFaceCounts).sort(([a], [b]) =>
    a.localeCompare(b),
  );
  if (entries.length === 0) {
    return (
      <p className="text-[11px] text-surface-500">No patches in polyMesh.</p>
    );
  }
  return (
    <div className="flex flex-wrap gap-1">
      {entries.map(([name, count]) => (
        <span
          key={name}
          className="rounded-sm border border-surface-700 bg-surface-800 px-1.5 py-0.5 font-mono text-[10px] text-surface-300"
          title={`${name}: ${count.toLocaleString()} faces`}
        >
          {name}
          <span className="ml-1 text-surface-500">·{count}</span>
        </span>
      ))}
    </div>
  );
}

function WarningList({
  warnings,
}: {
  warnings: { severity: MeshQualitySeverity; code: string; message: string }[];
}) {
  if (warnings.length === 0) return null;
  return (
    <ul className="mt-2 space-y-1 text-[11px]">
      {warnings.map((w, i) => {
        const tone =
          w.severity === "critical"
            ? "rose"
            : w.severity === "warning"
              ? "amber"
              : "green";
        return (
          <li
            key={`${w.code}-${i}`}
            className={`flex items-start gap-1.5 rounded-sm border px-2 py-1 ${TONE_BORDER[tone]} ${TONE_TEXT[tone]}`}
          >
            <code className="font-mono text-[10px] uppercase opacity-80">
              {w.code}
            </code>
            <span>{w.message}</span>
          </li>
        );
      })}
    </ul>
  );
}

function FailedChecksList({ checks }: { checks: string[] }) {
  if (checks.length === 0) return null;
  return (
    <ul className="mt-2 space-y-0.5 text-[11px] text-rose-200">
      {checks.map((c, i) => (
        <li key={i} className="flex items-start gap-1.5">
          <span aria-hidden="true">·</span>
          <span>{c}</span>
        </li>
      ))}
    </ul>
  );
}

// ────────── Main component ──────────

export function MeshQualityCard({ caseId, meshGenSeq }: MeshQualityCardProps) {
  const [state, setState] = useState<LoadState>({ status: "idle" });

  useEffect(() => {
    if (!caseId) return;
    let cancelled = false;
    setState({ status: "loading" });
    api
      .getMeshQuality(caseId, { runCheckmesh: true })
      .then((report) => {
        if (cancelled) return;
        setState({ status: "ready", report });
      })
      .catch((err) => {
        if (cancelled) return;
        let message = "mesh-quality fetch failed";
        if (err instanceof ApiError) {
          if (err.status === 404) {
            // case not yet meshed — defer rendering by re-entering idle.
            setState({ status: "idle" });
            return;
          }
          message = `${err.status}: ${err.message}`;
        } else if (err instanceof Error) {
          message = err.message;
        }
        setState({ status: "error", message });
      });
    return () => {
      cancelled = true;
    };
  }, [caseId, meshGenSeq]);

  if (state.status === "idle") return null;

  return (
    <section
      data-testid="mesh-quality-card"
      className="mt-2 rounded-sm border border-surface-700 bg-surface-900/50 p-2"
    >
      <header className="flex items-baseline justify-between">
        <h3 className="text-[12px] font-medium text-surface-200">
          Mesh quality
        </h3>
        {state.status === "ready" ? <VerdictPill report={state.report} /> : null}
      </header>

      {state.status === "loading" && (
        <p
          className="mt-2 font-mono text-[11px] text-surface-500"
          data-testid="mesh-quality-loading"
        >
          checking mesh…
        </p>
      )}

      {state.status === "error" && (
        <p
          data-testid="mesh-quality-error"
          className="mt-2 rounded-sm border border-rose-500/40 bg-rose-500/10 p-1.5 font-mono text-[11px] text-rose-200"
        >
          {state.message}
        </p>
      )}

      {state.status === "ready" && (
        <>
          <div className="mt-2 space-y-2">
            <QualityGauge
              label="max skewness"
              value={
                state.report.report_kind === "v126"
                  ? state.report.checkmesh_max_skewness
                  : null
              }
              bands={SKEWNESS_BANDS}
              axisMax={SKEWNESS_AXIS_MAX}
              format={(v) => v.toFixed(2)}
            />
            <QualityGauge
              label="max non-orthogonality"
              value={
                state.report.report_kind === "v126"
                  ? state.report.checkmesh_max_non_orthogonality_deg
                  : null
              }
              bands={NON_ORTHO_BANDS}
              axisMax={NON_ORTHO_AXIS_MAX}
              format={(v) => `${v.toFixed(1)}°`}
            />
            <QualityGauge
              label="max aspect ratio"
              value={
                state.report.report_kind === "v126"
                  ? state.report.checkmesh_max_aspect_ratio
                  : null
              }
              bands={ASPECT_RATIO_BANDS}
              axisMax={ASPECT_RATIO_AXIS_MAX}
              format={(v) => v.toFixed(0)}
              scale="log"
            />
          </div>
          {state.report.report_kind === "v126" &&
            state.report.checkmesh_n_severe_non_ortho_faces !== null &&
            state.report.checkmesh_n_severe_non_ortho_faces > 0 && (
              <p
                data-testid="mesh-quality-severe-faces"
                className="mt-2 rounded-sm border border-orange-500/40 bg-orange-500/10 px-2 py-1 font-mono text-[11px] text-orange-200"
              >
                ⚠ {state.report.checkmesh_n_severe_non_ortho_faces.toLocaleString()}{" "}
                severely non-orthogonal face
                {state.report.checkmesh_n_severe_non_ortho_faces === 1 ? "" : "s"}
              </p>
            )}
          {state.report.report_kind === "v126" &&
            state.report.checkmesh_failed_checks &&
            state.report.checkmesh_failed_checks.length > 0 && (
              <FailedChecksList checks={state.report.checkmesh_failed_checks} />
            )}
          <WarningList warnings={state.report.warnings} />
          <div className="mt-2 border-t border-surface-700/60 pt-2">
            <p className="mb-1 text-[10px] uppercase tracking-wider text-surface-500">
              boundary patches
            </p>
            <PatchChips patchFaceCounts={state.report.patch_face_counts} />
          </div>
        </>
      )}
    </section>
  );
}
