import { describe, expect, it } from "vitest";

import {
  DOE_BLUEPRINT_KPIS,
  DOE_BLUEPRINT_RIGHT_CARDS,
  DOE_BLUEPRINT_SAMPLES,
  DOE_BLUEPRINT_TABS,
  DOE_BLUEPRINT_VERDICT,
} from "../components/doeBlueprint";

describe("DOE blueprint contract", () => {
  it("keeps image-8 secondary tabs, sample matrix, and KPI strip auditable", () => {
    expect(DOE_BLUEPRINT_TABS.map((tab) => tab.label)).toEqual([
      "样本网格",
      "Pareto",
      "敏感性",
      "报告",
    ]);
    expect(DOE_BLUEPRINT_SAMPLES).toHaveLength(9);
    expect(DOE_BLUEPRINT_SAMPLES.filter((sample) => sample.recommended)).toHaveLength(5);
    expect(DOE_BLUEPRINT_KPIS).toMatchObject({
      sampleCount: 28,
      bestPressurePa: 212.6,
      bestTemperatureC: 94.1,
      bestVolumeM3: 18.42,
      bestGainPct: 4.2,
    });
  });

  it("keeps the selected DOE candidate tied to the best pressure-temperature-volume values", () => {
    const selected = DOE_BLUEPRINT_SAMPLES.find(
      (sample) => sample.id === DOE_BLUEPRINT_VERDICT.selectedId,
    );
    expect(selected).toMatchObject({
      id: "S-05",
      pressurePa: DOE_BLUEPRINT_KPIS.bestPressurePa,
      temperatureC: DOE_BLUEPRINT_KPIS.bestTemperatureC,
      volumeM3: DOE_BLUEPRINT_KPIS.bestVolumeM3,
      deltaPct: DOE_BLUEPRINT_KPIS.bestGainPct,
      recommended: true,
    });
    expect(DOE_BLUEPRINT_VERDICT.label).toBe("推荐设计 · S-05");
  });

  it("keeps the right-panel cards aligned to blueprint image 8 without claiming a live optimizer", () => {
    expect(DOE_BLUEPRINT_RIGHT_CARDS.map((card) => card.title)).toEqual([
      "推荐 5 个设计",
      "实验比对就绪",
      "导出报告",
    ]);
    expect(DOE_BLUEPRINT_RIGHT_CARDS.at(1)?.facts).toContainEqual({
      label: "后端状态",
      value: "待接入",
      tone: "warn",
    });
  });
});
