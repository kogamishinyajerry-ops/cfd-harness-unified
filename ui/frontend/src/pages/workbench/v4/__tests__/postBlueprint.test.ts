import { describe, expect, it } from "vitest";

import {
  POST_BLUEPRINT_KPIS,
  POST_BLUEPRINT_MINI_CHARTS,
  POST_BLUEPRINT_RADIAL_GAUGE,
  POST_BLUEPRINT_RIGHT_CARDS,
  POST_BLUEPRINT_TABS,
  POST_BLUEPRINT_VERDICT,
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

  it("keeps the comparator verdict pill and right-panel cards aligned to blueprint image 7", () => {
    expect(POST_BLUEPRINT_VERDICT).toMatchObject({
      label: "通过 · 对比基准",
      flowGainPct: 4.2,
      temperatureDeltaPct: 0.8,
    });
    expect(POST_BLUEPRINT_RIGHT_CARDS.map((card) => card.title)).toEqual([
      "对比基准 · 通过",
      "增益 +4.2%",
      "导出 PDF",
    ]);
  });
});
