/**
 * V4 · Mode renderer · 物理 (Physics) · per UI-SPEC §4.4
 *
 * 蓝图 3 视觉契合：半透 APU 外壳 + 内部真发动机几何。
 * Real-data wiring (2026-05-19):
 *   - When case has geometry.glb → ViewportV4 mounts vtk.js kernel and
 *     renders the actual case geometry (replaces the prior SVG cartoon
 *     IndustrialBoxScene that misled R3-R8 Codex reviews).
 *   - When no case yet → minimal "empty viewport" badge (no SVG fake).
 *
 * Materials & non-dimensional numbers in the right aside remain
 * advisor-derived; replacing those with case-real values is M5.5 (not
 * blocking the viewport-truthfulness arc).
 */
import { ViewportV4, type V4CameraPreset } from "../ViewportV4";
import { ModeTabStrip } from "../ModeTabStrip";
import {
  geometryGlbUrl,
  useGlbAvailability,
} from "../../hooks/useGlbAvailability";

const MATERIALS = [
  { name: "空气", rho: "1.225", mu: "1.8e-5" },
  { name: "钛合金", rho: "4506", mu: "—" },
  { name: "钢", rho: "7850", mu: "—" },
];

interface ModeRendererPhysicsProps {
  caseId: string | null | undefined;
  cameraPreset?: V4CameraPreset;
}

export function ModeRendererPhysics({
  caseId,
  cameraPreset = "iso",
}: ModeRendererPhysicsProps) {
  const glbUrl = geometryGlbUrl(caseId);
  const probe = useGlbAvailability(glbUrl);
  const hasGeometry = probe.available === true;

  return (
    <div data-testid="v4-mode-physics" className="flex h-full w-full flex-col bg-v4-canvas">
      <ModeTabStrip
        tabs={[
          { id: "recommended", label: "推荐物理模型" },
          { id: "custom", label: "自定义物理模型" },
          { id: "time", label: "时间格式" },
          { id: "gravity", label: "重力 g = 9.81" },
        ]}
        activeTabId="recommended"
        trailing={
          <span className="font-mono text-[10px]">
            稳态 · SST k-ω · Re 8.4e5 · Pr 0.71
          </span>
        }
      />
      <div className="flex min-h-0 flex-1">
        <div className="relative flex min-h-0 flex-1 items-center justify-center">
          {hasGeometry && glbUrl ? (
            <ViewportV4 glbUrl={glbUrl} cameraPreset={cameraPreset} />
          ) : (
            <EmptyViewport probing={probe.available === undefined} />
          )}
        </div>
        <aside className="flex w-[180px] shrink-0 flex-col border-l border-v4-border bg-v4-shell p-3">
          <div className="mb-2 text-[10px] uppercase tracking-wider text-v4-textTertiary">
            材料 · {MATERIALS.length}
          </div>
          <ul className="space-y-2">
            {MATERIALS.map((m) => (
              <li
                key={m.name}
                className="rounded border border-v4-border bg-v4-surfaceRaised px-2 py-1.5 text-[11px]"
              >
                <div className="text-v4-textPrimary">{m.name}</div>
                <div className="mt-0.5 flex justify-between font-mono text-[9px] text-v4-textTertiary">
                  <span>ρ {m.rho}</span>
                  <span>μ {m.mu}</span>
                </div>
              </li>
            ))}
          </ul>
          <div className="mt-3 border-t border-v4-border pt-2 text-[10px] text-v4-textTertiary">
            <div className="flex justify-between">
              <span>Re</span>
              <span className="font-mono text-v4-textPrimary">8.4e5</span>
            </div>
            <div className="flex justify-between">
              <span>Pr</span>
              <span className="font-mono text-v4-textPrimary">0.71</span>
            </div>
            <div className="flex justify-between">
              <span>Ma</span>
              <span className="font-mono text-v4-textPrimary">0.18</span>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

/** Replaces the prior IndustrialBoxScene SVG cartoon — honest empty
 *  state when no case geometry has been ingested. */
function EmptyViewport({ probing }: { probing: boolean }) {
  return (
    <div
      data-testid="v4-physics-empty-viewport"
      className="flex h-full w-full flex-col items-center justify-center gap-2 text-v4-textTertiary"
    >
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" opacity="0.4">
        <path d="M12 2L2 7v10l10 5 10-5V7L12 2z" />
        <path d="M2 7l10 5 10-5" />
        <path d="M12 22V12" />
      </svg>
      <div className="text-[11px]">
        {probing ? "正在探测几何…" : "无案例几何 · 先在导入步骤上传"}
      </div>
    </div>
  );
}
