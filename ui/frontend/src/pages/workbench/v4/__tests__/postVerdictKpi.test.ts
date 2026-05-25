/**
 * DEC-V61-205 (M5 C4) · the Post KPI strip's 对比基准 chip maps the REAL
 * comparison verdict, with an honest no-baseline state and — per Codex R1
 * P3 — a distinct loading state so a gold-standard case never flashes a
 * false "无基准" before its PASS/FAIL resolves. Pure mapping test.
 */
import { describe, expect, it } from "vitest";

import { postVerdictKpi } from "../components/KpiStripV4";
import type { PostVerdict } from "../hooks/useComparisonVerdict";

const v = (over: Partial<PostVerdict>): PostVerdict => ({
  state: "none",
  level: null,
  detail: null,
  nPass: null,
  nTotal: null,
  ...over,
});

describe("postVerdictKpi (M5 C4 对比基准 chip)", () => {
  it("renders the gold-point count + conclusion for a real verdict", () => {
    const pass = postVerdictKpi(v({ state: "verdict", level: "PASS", nPass: 17, nTotal: 17 }));
    expect(pass.value).toBe("17/17");
    expect(pass.delta).toBe("通过");
    expect(pass.deltaTone).toBe("healthy");

    const fail = postVerdictKpi(v({ state: "verdict", level: "FAIL", nPass: 3, nTotal: 17 }));
    expect(fail.delta).toBe("未通过");
    expect(fail.deltaTone).toBe("crit");
  });

  it("shows an honest no-baseline state when there is no gold reference", () => {
    expect(postVerdictKpi(v({ state: "none" })).value).toBe("无基准");
  });

  it("shows a service-error state distinctly from no-baseline", () => {
    expect(postVerdictKpi(v({ state: "error" })).value).toBe("不可用");
  });

  it("shows a pending state while loading — NOT a false 无基准 (R1 P3)", () => {
    const chip = postVerdictKpi(v({ state: "loading" }));
    expect(chip.value).toBe("…");
    expect(chip.value).not.toBe("无基准");
  });
});
