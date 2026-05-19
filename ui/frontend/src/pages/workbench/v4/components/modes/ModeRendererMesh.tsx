/**
 * V4 · Mode renderer · 网格 (Mesh) · per UI-SPEC §4.3 · Phase C-R3 wired.
 *
 * Real polyMesh wireframe (mesh.glb · LINES primitive) when the case
 * has run sHM; falls back to the stylised SVG enclosure otherwise.
 *
 * Phase C-R3: bottom strip now binds to MeshMetrics from
 * useV4WorkbenchContext — 4 QC band pills (gci_32 / asymptotic_range /
 * richardson_p / n_levels color-coded green/yellow/red/gray), a
 * density-refinement bar chart (densities[].n_cells_1d), and key GCI
 * chips (gci_32_pct, p_obs, n_levels count). The old 5 hardcoded
 * histograms are gone — those were per-cell statistics the backend
 * doesn't currently expose; Richardson grid-convergence is the
 * authoritative mesh-quality signal we DO have.
 */
import { useV4WorkbenchContext } from "../../hooks/useV4WorkbenchContext";
import {
  meshGlbUrl,
  useGlbAvailability,
} from "../../hooks/useGlbAvailability";
import { IndustrialBoxScene } from "../scene/IndustrialBoxScene";
import { ModeTabStrip } from "../ModeTabStrip";
import { ViewportV4, type V4CameraPreset } from "../ViewportV4";
import { V4_PALETTE } from "@/theme/industrial_minimalist";
import type { QcVerdict } from "@/types/mesh_metrics";

const QC_COLOR: Record<QcVerdict, string> = {
  green: V4_PALETTE.healthy,
  yellow: V4_PALETTE.warn,
  red: V4_PALETTE.crit,
  gray: V4_PALETTE.textTertiary,
};

const QC_LABEL: Record<string, string> = {
  gci_32: "GCI₃₂",
  asymptotic_range: "渐进区",
  richardson_p: "Richardson p",
  n_levels: "层级数",
};

function fmtPct(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  if (Math.abs(n) >= 100) return n.toFixed(1);
  return n.toFixed(2);
}

function fmt(n: number | null | undefined, digits = 2): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return n.toFixed(digits);
}

function MeshOverlay() {
  const lines: string[] = [];
  for (let i = 1; i < 10; i++) {
    const t = i / 10;
    const y = 10 + t * 180;
    lines.push(`M 200,${y.toFixed(1)} L 600,${y.toFixed(1)}`);
  }
  for (let i = 1; i < 14; i++) {
    const t = i / 14;
    const x = 200 + t * 400;
    lines.push(`M ${x.toFixed(1)},10 L ${x.toFixed(1)},190`);
  }
  return (
    <g pointerEvents="none" opacity="0.45">
      {lines.map((d, i) => (
        <path key={i} d={d} stroke={V4_PALETTE.border} strokeWidth="0.3" fill="none" />
      ))}
    </g>
  );
}

interface QcPillProps {
  label: string;
  verdict: QcVerdict;
}

function QcPill({ label, verdict }: QcPillProps) {
  return (
    <div
      className="flex flex-1 items-center gap-2 rounded border border-v4-border bg-v4-surfaceRaised px-3 py-2"
      data-testid={`mesh-qc-pill-${label}`}
      data-verdict={verdict}
    >
      <span
        aria-hidden
        className="h-2 w-2 shrink-0 rounded-full"
        style={{ backgroundColor: QC_COLOR[verdict] }}
      />
      <span className="flex-1 text-[10px] text-v4-textSecondary">{label}</span>
      <span
        className="font-mono text-[10px] uppercase tracking-wider"
        style={{ color: QC_COLOR[verdict] }}
      >
        {verdict}
      </span>
    </div>
  );
}

interface DensityChartProps {
  densities: { n_cells_1d: number; value: number | null; has_value: boolean }[];
  fExtrapolated: number | null | undefined;
}

function DensityChart({ densities, fExtrapolated }: DensityChartProps) {
  if (densities.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center rounded border border-v4-border bg-v4-surfaceRaised text-[10px] text-v4-textTertiary">
        —
      </div>
    );
  }
  const points = densities.filter((d) => d.has_value && d.value != null);
  const values = points.map((d) => d.value as number);
  const minV = Math.min(...values, fExtrapolated ?? Infinity);
  const maxV = Math.max(...values, fExtrapolated ?? -Infinity);
  const rangeV = Math.max(1e-9, maxV - minV);

  return (
    <div className="flex flex-1 flex-col rounded border border-v4-border bg-v4-surfaceRaised px-3 py-2">
      <div className="flex items-baseline justify-between text-[10px]">
        <span className="text-v4-textSecondary">网格细化收敛</span>
        <span className="font-mono text-v4-textTertiary">
          {densities.length} 级 · h⁻¹ ↑
        </span>
      </div>
      <svg viewBox="0 0 200 56" preserveAspectRatio="none" className="h-12 w-full">
        {/* h_extrapolated reference line */}
        {fExtrapolated != null && Number.isFinite(fExtrapolated) && (
          <line
            x1="0"
            x2="200"
            y1={48 - ((fExtrapolated - minV) / rangeV) * 40}
            y2={48 - ((fExtrapolated - minV) / rangeV) * 40}
            stroke={V4_PALETTE.healthy}
            strokeWidth="0.6"
            strokeDasharray="3 2"
            opacity="0.65"
          />
        )}
        {/* density points connected */}
        <polyline
          points={densities
            .map((d, i) => {
              const x = (i / Math.max(1, densities.length - 1)) * 192 + 4;
              const v = d.value;
              const y =
                v != null && Number.isFinite(v)
                  ? 48 - ((v - minV) / rangeV) * 40
                  : 48;
              return `${x.toFixed(1)},${y.toFixed(1)}`;
            })
            .join(" ")}
          fill="none"
          stroke={V4_PALETTE.brand}
          strokeWidth="1.4"
        />
        {densities.map((d, i) => {
          const x = (i / Math.max(1, densities.length - 1)) * 192 + 4;
          const v = d.value;
          const y =
            v != null && Number.isFinite(v)
              ? 48 - ((v - minV) / rangeV) * 40
              : 48;
          const isLast = i === densities.length - 1;
          return (
            <g key={d.n_cells_1d}>
              <circle
                cx={x}
                cy={y}
                r={isLast ? 2.2 : 1.6}
                fill={isLast ? V4_PALETTE.active : V4_PALETTE.brand}
              />
              <text
                x={x}
                y={54}
                textAnchor="middle"
                fontSize="6"
                fill={V4_PALETTE.textTertiary}
                fontFamily="ui-monospace"
              >
                {d.n_cells_1d}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

interface Props {
  caseId?: string;
  cameraPreset?: V4CameraPreset;
}

export function ModeRendererMesh({ caseId, cameraPreset }: Props) {
  const ctx = useV4WorkbenchContext(caseId ?? null);
  const glbUrl = meshGlbUrl(caseId);
  const probe = useGlbAvailability(glbUrl);
  const showViewport = probe.available === true;

  const mesh = ctx.meshMetrics;
  const qc = mesh?.qc_band;
  const gci = mesh?.gci;
  const densities = mesh?.densities ?? [];
  const lastDensity = densities[densities.length - 1];
  const trailing = mesh
    ? `${densities.length} 级 · 最细 ${lastDensity?.n_cells_1d ?? "—"} · GCI₃₂ ${fmtPct(gci?.gci_32_pct)}%`
    : "等待 mesh metrics";

  return (
    <div data-testid="v4-mode-mesh" className="flex h-full w-full flex-col bg-v4-canvas">
      <ModeTabStrip
        tabs={[
          { id: "quality", label: "网格质量" },
          { id: "cell-type", label: "单元类型" },
          { id: "slice", label: "切片" },
        ]}
        activeTabId="quality"
        trailing={<span className="font-mono text-[10px]">{trailing}</span>}
      />
      <div className="relative flex min-h-0 flex-1 items-center justify-center">
        {showViewport ? (
          <ViewportV4 glbUrl={glbUrl} cameraPreset={cameraPreset ?? "iso"} />
        ) : (
          <div className="flex h-full w-full items-center justify-center px-6 py-4">
            <IndustrialBoxScene variant="mesh" className="h-full max-h-[400px] w-full max-w-3xl">
              <MeshOverlay />
            </IndustrialBoxScene>
          </div>
        )}
        {probe.isLoading && (
          <div className="pointer-events-none absolute left-3 top-3 rounded border border-v4-border bg-v4-surfaceRaised/90 px-2 py-0.5 font-mono text-[10px] text-v4-textTertiary">
            检查网格…
          </div>
        )}
        {probe.available === false && caseId && (
          <div
            className="pointer-events-none absolute right-3 bottom-3 rounded border border-v4-border bg-v4-surfaceRaised/90 px-2 py-0.5 font-mono text-[10px] text-v4-textTertiary"
            data-testid="v4-mode-mesh-empty-state"
          >
            当前算例无 polyMesh · 显示示意场景
          </div>
        )}
        {gci && (
          <div className="pointer-events-none absolute right-3 top-3 flex gap-2 text-[10px]">
            <span className="rounded border border-v4-border bg-v4-surfaceRaised/95 px-2 py-1">
              <span className="text-v4-textTertiary">f_∞ </span>
              <span className="font-mono text-v4-textPrimary">
                {fmt(gci.f_extrapolated, 4)}
              </span>
            </span>
            <span className="rounded border border-v4-border bg-v4-surfaceRaised/95 px-2 py-1">
              <span className="text-v4-textTertiary">p_obs </span>
              <span className="font-mono text-v4-textPrimary">
                {fmt(gci.p_obs, 2)}
              </span>
            </span>
            {gci.asymptotic_range_ok != null && (
              <span
                className="rounded border bg-v4-surfaceRaised/95 px-2 py-1"
                style={{
                  borderColor: gci.asymptotic_range_ok
                    ? V4_PALETTE.healthy + "80"
                    : V4_PALETTE.warn + "80",
                  color: gci.asymptotic_range_ok
                    ? V4_PALETTE.healthy
                    : V4_PALETTE.warn,
                }}
              >
                渐进区 {gci.asymptotic_range_ok ? "✓" : "✗"}
              </span>
            )}
          </div>
        )}
      </div>
      <div
        className="flex h-24 shrink-0 items-center gap-2 border-t border-v4-border bg-v4-shell px-3"
        data-testid="mesh-qc-strip"
        data-has-metrics={mesh ? "true" : "false"}
      >
        {qc ? (
          <>
            {(["gci_32", "asymptotic_range", "richardson_p", "n_levels"] as const).map(
              (k) => (
                <QcPill key={k} label={QC_LABEL[k]} verdict={qc[k]} />
              ),
            )}
            <DensityChart
              densities={densities}
              fExtrapolated={gci?.f_extrapolated}
            />
          </>
        ) : (
          <div className="flex flex-1 items-center justify-center rounded border border-dashed border-v4-border bg-v4-surfaceRaised/40 text-[11px] text-v4-textTertiary">
            {caseId ? "等待 mesh metrics 数据" : "未选择算例"}
          </div>
        )}
      </div>
    </div>
  );
}
