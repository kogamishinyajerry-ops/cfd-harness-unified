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
 * R1 P2 + R2 P3 fix: aspect-ratio bands span 10 / 100 / 1000 / 10000.
 * Log scale uses canonical
 *   (log10(value) - log10(axisMin)) / (log10(axisMax) - log10(axisMin))
 * so each decade gets EXACTLY equal width. ``axisMin=1`` for aspect
 * ratio because a cell with AR < 1 is geometrically impossible —
 * R2 P3 closure: the prior `log10(value+1)` form treated the
 * impossible 0..1 interval as ~7.5% of the bar, shrinking the
 * "good" 1..10 decade. Linear stays default for skewness (0..1) and
 * non-orthogonality (0..90) where bands are already evenly spaced.
 */
function clampPercent(
  value: number,
  axisMax: number,
  scale: AxisScale = "linear",
  axisMin = 0,
): number {
  if (!isFinite(value)) return 0;
  if (scale === "log") {
    const lo = Math.max(axisMin, 1); // log scale requires positive axisMin
    if (value <= lo) return 0;
    if (value >= axisMax) return 100;
    return ((Math.log10(value) - Math.log10(lo)) /
      (Math.log10(axisMax) - Math.log10(lo))) *
      100;
  }
  if (value <= axisMin) return 0;
  if (value >= axisMax) return 100;
  return ((value - axisMin) / (axisMax - axisMin)) * 100;
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
    // base-review-2 P2 closure: checkmesh_failed_checks is populated
    // only when the backend can scrape `***` lines from checkMesh
    // output. If mesh_ok=false but no detail lines were parsed, the
    // prior "Failed 0 checks" text was factually wrong — fall back to
    // "Mesh failed" with no count, which is honest about the gap.
    const n = report.checkmesh_failed_checks?.length ?? 0;
    return (
      <span className="rounded-sm border border-rose-500/40 bg-rose-500/15 px-2 py-0.5 font-mono text-[11px] text-rose-200">
        {n > 0 ? `Failed ${n} check${n === 1 ? "" : "s"}` : "Mesh failed"}
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
  /** R2 P3: minimum physically-meaningful axis value. For aspect ratio
   *  the floor is 1 (a cell with AR<1 is geometrically impossible),
   *  so the gauge starts at 1 not 0. Defaults to 0 for linear gauges. */
  axisMin?: number;
}

function QualityGauge({
  label,
  value,
  bands,
  axisMax,
  format,
  scale = "linear",
  axisMin = scale === "log" ? 1 : 0,
}: QualityGaugeProps) {
  // Render the band ladder as a stacked horizontal bar with a needle
  // overlay at the current value. When value is null (skipped), render
  // the band ladder dimmed with no needle so the reader still sees the
  // threshold geography.
  const skipped = value === null;
  const band = !skipped ? classifyValue(value, bands) : null;
  const needlePercent = !skipped
    ? clampPercent(value, axisMax, scale, axisMin)
    : 0;
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
          // 10/100/1000 aspect-ratio bands to <10% combined. R2 P3
          // closure: anchor on axisMin so the impossible <axisMin
          // interval doesn't consume bar width.
          const prevMax = i === 0 ? axisMin : (bands[i - 1].max ?? axisMax);
          const cap = b.max === null ? axisMax : Math.min(b.max, axisMax);
          const startPct = clampPercent(prevMax, axisMax, scale, axisMin);
          const endPct = clampPercent(cap, axisMax, scale, axisMin);
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

// V128 R0 + V129a: per-chip tone derivation. The V128 baseline derived
// from checkmesh_mesh_ok + patch_face_counts; V129a adds REAL per-patch
// data when the backend supplies
// `checkmesh_n_severe_non_ortho_faces_per_patch`.
// Rules (highest precedence first):
//   * face_count === 0          → 'rose' (zero-face patch always wrong)
//   * V129a per-patch severe>0  → 'rose' (this patch has severe faces)
//   * V129a per-patch severe===0 → 'green' (this patch is clean even
//                                   if mesh_ok=false elsewhere)
//   * V126 mesh_ok === false    → 'amber' (V128 fallback when V129a
//                                  per-patch dict absent — global
//                                  failure but no localization)
//   * V126 mesh_ok === true     → 'green' (V128 fallback)
//   * V126 mesh_ok === null OR
//     V122 fallback             → 'neutral' (existing grey)
type PatchTone = "neutral" | "green" | "amber" | "rose";

function derivePatchTone(
  patchName: string,
  faceCount: number,
  report: MeshQualityReport,
): PatchTone {
  if (faceCount === 0) return "rose";
  if (report.report_kind !== "v126") return "neutral";
  // V129a + base-review-2 P2 closure: the per-patch dict only
  // localizes severe non-orthogonality — it does NOT account for
  // skewness / aspect-ratio / other checkMesh failures. So a patch
  // with severe=0 is "clean for non-ortho", not necessarily "clean
  // for all checks". We use mesh_ok as the global tiebreaker:
  //   * severe>0 (any mesh_ok)        → rose (this patch IS implicated)
  //   * severe=0 + mesh_ok=true       → green (genuinely clean)
  //   * severe=0 + mesh_ok=false      → amber (non-ortho fine HERE,
  //                                     but mesh failed elsewhere —
  //                                     localization unknown)
  //   * severe=0 + mesh_ok=null       → neutral (graceful degrade)
  const perPatch = report.checkmesh_n_severe_non_ortho_faces_per_patch;
  if (perPatch !== null && patchName in perPatch) {
    if (perPatch[patchName] > 0) return "rose";
    if (report.checkmesh_mesh_ok === true) return "green";
    if (report.checkmesh_mesh_ok === false) return "amber";
    return "neutral";
  }
  // V128 fallback when V129a dict absent (older backend, container
  // unavailable, or no severe faces written so per-patch is null).
  if (report.checkmesh_mesh_ok === null) return "neutral";
  return report.checkmesh_mesh_ok ? "green" : "amber";
}

const PATCH_TONE_CLASS: Record<PatchTone, string> = {
  neutral: "border-surface-700 bg-surface-800 text-surface-300",
  green: "border-emerald-500/40 bg-emerald-500/10 text-emerald-200",
  amber: "border-amber-500/40 bg-amber-500/10 text-amber-200",
  rose: "border-rose-500/40 bg-rose-500/15 text-rose-200",
};

function PatchChips({
  patchFaceCounts,
  report,
}: {
  patchFaceCounts: Record<string, number>;
  report: MeshQualityReport;
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
      {entries.map(([name, count]) => {
        const tone = derivePatchTone(name, count, report);
        // a11y: zero-face patches get an explicit "empty" text label so
        // color-blind users see the same signal as the rose tone.
        // V129a: when per-patch severe count is available and >0,
        // surface the count in the chip text (e.g. "·1500 faces ·3 severe")
        // so color-blind users get the localized signal.
        const isEmpty = count === 0;
        const perPatch =
          report.report_kind === "v126"
            ? report.checkmesh_n_severe_non_ortho_faces_per_patch
            : null;
        const severeCount = perPatch?.[name] ?? 0;
        const stateLabel = isEmpty
          ? "empty"
          : severeCount > 0
            ? `${count.toLocaleString()} faces · ${severeCount} severe`
            : `${count.toLocaleString()} faces`;
        return (
          <span
            key={name}
            data-testid={`patch-chip-${name}`}
            data-tone={tone}
            className={`rounded-sm border px-1.5 py-0.5 font-mono text-[10px] ${PATCH_TONE_CLASS[tone]}`}
            title={`${name}: ${stateLabel}`}
          >
            {name}
            <span className="ml-1 opacity-70">
              {isEmpty
                ? "· empty"
                : severeCount > 0
                  ? `·${count} ·${severeCount} severe`
                  : `·${count}`}
            </span>
          </span>
        );
      })}
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

/** R2 P2 + R3 P1: module-level cache so remounting the card on
 *  Step 2 ↔ 3/4 navigation doesn't re-run Docker checkMesh against
 *  an unchanged mesh. Keyed by ``caseId`` ONLY (R3 P1 closure: prior
 *  ``${caseId}:${meshGenSeq}`` keying was broken because meshGenSeq
 *  lived in Step2Mesh local state and reset to 0 on remount). The
 *  cache is invalidated on:
 *    1. local meshImported() success (Step2Mesh's triggerMesh)
 *    2. ai-coach:proposal-applied for regenerate_mesh (registered at
 *       module level so it fires regardless of which step is mounted)
 *    3. R3 P2: V126 graceful-degradation responses (checkmesh_mesh_ok
 *       === null) NOT cached so operator starting the container later
 *       gets a fresh fetch on next remount
 */
const meshQualityCache = new Map<string, LoadState>();

/** Invalidate one or all entries. Called by Step2Mesh after a fresh
 *  mesh lands and by the module-level regenerate_mesh listener so the
 *  next remount fetches against the new polyMesh. */
export function invalidateMeshQualityCache(caseId?: string): void {
  if (caseId === undefined) {
    meshQualityCache.clear();
  } else {
    meshQualityCache.delete(caseId);
  }
}

/** Test-only export: clear the module-level cache so tests with
 *  re-used caseIds don't see stale state from prior runs. */
export function __clearMeshQualityCacheForTests(): void {
  meshQualityCache.clear();
}

// R3 P1 + R4 P2: register cache-invalidation listeners at module level
// so any mesh mutation busts the cache regardless of which step is
// mounted. Idempotent — safe to register once at module load.
//   * ai-coach:proposal-applied (tool=regenerate_mesh) — AI-driven mesh
//     regeneration via the coach proposal pipeline.
//   * mesh:mutated — fired by api/client.ts on every polyMesh-mutating
//     route (meshImported, setupBC, setupBCWithEnvelope). This catches
//     Step 3's BC setup (rewrites constant/polyMesh/boundary) and the
//     legacy /workbench/case/:caseId/mesh wizard, neither of which
//     went through Step2Mesh's local invalidation path before R4.
if (typeof window !== "undefined") {
  window.addEventListener("ai-coach:proposal-applied", (e) => {
    const evt = e as CustomEvent<{ caseId?: string; tool?: string }>;
    if (
      typeof evt.detail?.caseId === "string" &&
      evt.detail?.tool === "regenerate_mesh"
    ) {
      invalidateMeshQualityCache(evt.detail.caseId);
    }
  });
  window.addEventListener("mesh:mutated", (e) => {
    const evt = e as CustomEvent<{ caseId?: string }>;
    if (typeof evt.detail?.caseId === "string") {
      invalidateMeshQualityCache(evt.detail.caseId);
    }
  });
}

export function MeshQualityCard({ caseId, meshGenSeq }: MeshQualityCardProps) {
  const [state, setState] = useState<LoadState>(() => {
    const cached = meshQualityCache.get(caseId);
    return cached ?? { status: "idle" };
  });

  useEffect(() => {
    if (!caseId) return;
    // Cache hit: render the prior result instantly, no network.
    const cached = meshQualityCache.get(caseId);
    if (cached && cached.status === "ready") {
      setState(cached);
      return;
    }
    let cancelled = false;
    setState({ status: "loading" });
    api
      .getMeshQuality(caseId, { runCheckmesh: true })
      .then((report) => {
        if (cancelled) return;
        const next: LoadState = { status: "ready", report };
        // R3 P2: don't cache V126 graceful-degradation responses
        // (checkmesh_mesh_ok=null means cfd-openfoam container was
        // unavailable). If the operator starts the container later
        // and revisits Step 2, a cached "skipped" entry would
        // suppress the retry — leave the entry uncached so next
        // remount tries again.
        const isGracefulDegrade =
          report.report_kind === "v126" && report.checkmesh_mesh_ok === null;
        if (!isGracefulDegrade) {
          meshQualityCache.set(caseId, next);
        }
        setState(next);
      })
      .catch((err) => {
        if (cancelled) return;
        let message = "mesh-quality fetch failed";
        if (err instanceof ApiError) {
          if (err.status === 404) {
            // case not yet meshed — defer rendering by re-entering idle.
            // Don't cache 404; the next mesh attempt should fire a
            // fresh GET.
            setState({ status: "idle" });
            return;
          }
          message = `${err.status}: ${err.message}`;
        } else if (err instanceof Error) {
          message = err.message;
        }
        // Don't cache errors either — we want the next remount to
        // retry rather than render the stale failure.
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
            <PatchChips
              patchFaceCounts={state.report.patch_face_counts}
              report={state.report}
            />
          </div>
        </>
      )}
    </section>
  );
}
