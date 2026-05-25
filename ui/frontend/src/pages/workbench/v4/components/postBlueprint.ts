import { V4_CFD_COLORMAP, V4_PALETTE } from "@/theme/industrial_minimalist";
import type { ModeTab } from "./ModeTabStrip";

export interface PostBlueprintMiniChart {
  id: "pressure" | "velocity" | "temperature";
  label: string;
  unit: string;
  color: string;
  samples: number[];
}

export const POST_BLUEPRINT_TABS: ModeTab[] = [
  { id: "pv", label: "逐层 PV" },
  { id: "iso", label: "等值面" },
  { id: "analysis", label: "分析" },
  { id: "video", label: "视频" },
  { id: "render", label: "渲染" },
];

// DEC-V61-205 · de-fake history. A truth-chain workbench must not ship
// fabricated telemetry, so the following blueprint constants were RETIRED:
//   • M5 C3 — POST_BLUEPRINT_VERDICT ("通过 · +4.2%"): the Post verdict pill
//     now renders the REAL gold-vs-measured verdict (useComparisonVerdict).
//   • M5 C4 — POST_BLUEPRINT_KPIS (248.6 Pa / 3.62 kg/s / 96.4°C / +4.2%):
//     the KpiStripV4 post strip now reports REAL run facts (success / 用时 /
//     退出码 / 残差 p) + the real verdict.
//   • M5 C4 — POST_BLUEPRINT_RADIAL_GAUGE (65% "通过率"): the radial gauge now
//     reads REAL residual convergence (useResidualSeries.convergenceGauge…).
//   • M5 C4 — POST_BLUEPRINT_RIGHT_CARDS ("对比基准·通过 / 增益+4.2% / 导出 PDF"):
//     RightPanelV4 post cards now report real run facts + verdict + an honest
//     evidence-artifact card (no fake PDF-export affordance).
// They were deleted (not just unused) so they cannot silently re-fake later.

// The three profile waveforms below are ILLUSTRATIVE design tokens only — the
// workbench has no per-quantity profile source for a generic imported case.
// ModeRendererPost renders them with an explicit "示意" badge + muted styling
// (illustrative prop) and hides the terminal value, so they never masquerade
// as run data (charter: honest blueprint-labelled states).
export const POST_BLUEPRINT_MINI_CHARTS: PostBlueprintMiniChart[] = [
  {
    id: "pressure",
    label: "压力剖面",
    unit: "Pa",
    color: V4_CFD_COLORMAP[4],
    samples: [216, 224, 232, 238, 242, 245, 247, 248, 248.2, 248.5, 248.6],
  },
  {
    id: "velocity",
    label: "速度剖面",
    unit: "m/s",
    color: V4_CFD_COLORMAP[1],
    samples: [22.4, 26.1, 30.4, 34.8, 37.5, 39.6, 40.8, 41.6, 42.1, 42.4, 42.6],
  },
  {
    id: "temperature",
    label: "温度剖面",
    unit: "°C",
    color: V4_PALETTE.warn,
    samples: [88.1, 90.2, 91.8, 93.0, 94.0, 94.8, 95.3, 95.8, 96.1, 96.3, 96.4],
  },
];
