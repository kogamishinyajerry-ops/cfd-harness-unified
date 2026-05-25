import { describe, expect, it } from "vitest";

import * as postBlueprint from "../components/postBlueprint";
import {
  POST_BLUEPRINT_MINI_CHARTS,
  POST_BLUEPRINT_TABS,
} from "../components/postBlueprint";

describe("Post blueprint contract", () => {
  it("keeps the secondary tabs mechanically auditable", () => {
    expect(POST_BLUEPRINT_TABS.map((tab) => tab.label)).toEqual([
      "逐层 PV",
      "等值面",
      "分析",
      "视频",
      "渲染",
    ]);
  });

  it("keeps the three illustrative profile tokens (rendered as 示意, not run data)", () => {
    expect(POST_BLUEPRINT_MINI_CHARTS.map((chart) => chart.label)).toEqual([
      "压力剖面",
      "速度剖面",
      "温度剖面",
    ]);
    for (const chart of POST_BLUEPRINT_MINI_CHARTS) {
      expect(chart.samples.length).toBeGreaterThanOrEqual(10);
    }
  });

  // DEC-V61-205 (M5 C3 + C4): the fabricated telemetry constants were DELETED
  // (not merely unused) so they cannot silently re-fake. The Post surfaces now
  // render real run facts + the real comparison verdict (useComparisonVerdict /
  // useResidualSeries) or honest no-baseline / illustrative states.
  it("has retired every fabricated-telemetry constant", () => {
    expect("POST_BLUEPRINT_VERDICT" in postBlueprint).toBe(false);
    expect("POST_BLUEPRINT_KPIS" in postBlueprint).toBe(false);
    expect("POST_BLUEPRINT_RADIAL_GAUGE" in postBlueprint).toBe(false);
    expect("POST_BLUEPRINT_RIGHT_CARDS" in postBlueprint).toBe(false);
  });
});
