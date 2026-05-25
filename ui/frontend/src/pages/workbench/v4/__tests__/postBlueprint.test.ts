import { describe, expect, it } from "vitest";

import {
  POST_BLUEPRINT_KPIS,
  POST_BLUEPRINT_MINI_CHARTS,
  POST_BLUEPRINT_RADIAL_GAUGE,
  POST_BLUEPRINT_RIGHT_CARDS,
  POST_BLUEPRINT_TABS,
} from "../components/postBlueprint";

describe("Post blueprint contract", () => {
  it("keeps image-7 secondary tabs and KPI strip mechanically auditable", () => {
    expect(POST_BLUEPRINT_TABS.map((tab) => tab.label)).toEqual([
      "逐层 PV",
      "等值面",
      "分析",
      "视频",
      "渲染",
    ]);
    expect(POST_BLUEPRINT_KPIS).toMatchObject({
      pressurePa: 248.6,
      massFlowKgS: 3.62,
      temperatureC: 96.4,
      progressPct: 65,
      gainPct: 4.2,
    });
  });

  it("keeps the right telemetry strip split into three profiles and one radial gauge", () => {
    expect(POST_BLUEPRINT_MINI_CHARTS.map((chart) => chart.label)).toEqual([
      "压力剖面",
      "速度剖面",
      "温度剖面",
    ]);
    for (const chart of POST_BLUEPRINT_MINI_CHARTS) {
      expect(chart.samples.length).toBeGreaterThanOrEqual(10);
    }
    expect(POST_BLUEPRINT_RADIAL_GAUGE.valuePct).toBe(65);
  });

  // M5 C3: the hardcoded POST_BLUEPRINT_VERDICT was removed — the Post
  // verdict pill renders the real comparison verdict (useComparisonVerdict)
  // or an honest no-baseline state. The right-panel cards remain blueprint
  // placeholders pending M5 C4 (honest-ify / back with real run data).
  it("keeps the right-panel blueprint cards stable pending C4", () => {
    expect(POST_BLUEPRINT_RIGHT_CARDS.map((card) => card.title)).toEqual([
      "对比基准 · 通过",
      "增益 +4.2%",
      "导出 PDF",
    ]);
  });
});
