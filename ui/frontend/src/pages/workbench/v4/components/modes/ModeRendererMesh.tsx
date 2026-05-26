/**
 * V4 · Mode renderer · 网格 (Mesh) · per UI-SPEC §4.3 · Phase C-R3 wired.
 *
 * Real polyMesh wireframe (mesh.glb · LINES primitive) when the case
 * has run sHM; falls back to the stylised SVG enclosure otherwise.
 *
 * Blueprint image 4: MainCanvas owns the wireframe mesh layer, while the
 * global KpiStripV4 renders the 5 horizontal mesh-quality histograms +
 * second-row numeric contract.
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

function fmt(n: number | null | undefined, digits = 2): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return n.toFixed(digits);
}

function MeshOverlay() {
  const lines: string[] = [];

  // Back wall + enclosure subdivision.
  for (let i = 1; i < 12; i++) {
    const y = 10 + (i / 12) * 180;
    lines.push(`M 200,${y.toFixed(1)} L 600,${y.toFixed(1)}`);
  }
  for (let i = 1; i < 18; i++) {
    const x = 200 + (i / 18) * 400;
    lines.push(`M ${x.toFixed(1)},10 L ${x.toFixed(1)},190`);
  }
  for (let i = 1; i < 9; i++) {
    const x1 = 80 + i * 45;
    const x2 = 200 + i * 45;
    lines.push(`M ${x1},240 L ${x2},190`);
  }

  // Engine body wireframe subdivisions.
  for (let x = 245; x <= 415; x += 17) {
    lines.push(`M ${x},118 L ${x},182`);
  }
  for (let y = 130; y <= 170; y += 10) {
    lines.push(`M 230,${y} L 430,${y}`);
  }
  for (let y = 124; y <= 176; y += 13) {
    lines.push(`M 430,${y} L 488,150`);
  }

  return (
    <g pointerEvents="none" opacity="0.58" data-testid="v4-mode-mesh-wireframe-overlay">
      {lines.map((d, i) => (
        <path
          key={i}
          d={d}
          stroke={i % 3 === 0 ? V4_PALETTE.brand : V4_PALETTE.borderActive}
          strokeWidth={i % 3 === 0 ? "0.42" : "0.28"}
          fill="none"
        />
      ))}
    </g>
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
  const gci = mesh?.gci;
  const densities = mesh?.densities ?? [];
  const lastDensity = densities[densities.length - 1];
  // Honest trailing: real mesh-metrics summary when present, else an explicit
  // no-metrics state — never a fabricated cell-count/skewness (M5.5 truth-chain
  // de-fake · DEC-V61-206).
  const trailing = mesh
    ? `${densities.length} 级 · 最细 ${lastDensity?.n_cells_1d ?? "—"} · GCI 数据`
    : "尚无网格指标 · 先生成网格";

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
        {probe.available === true && (
          <div
            className="pointer-events-none absolute left-3 bottom-3 rounded border border-v4-border bg-v4-surfaceRaised/90 px-2 py-0.5 font-mono text-[10px] text-v4-textTertiary"
            data-testid="v4-mode-mesh-wireframe-source"
          >
            mesh.glb 线框层 · QA histogram 已接入
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
    </div>
  );
}
