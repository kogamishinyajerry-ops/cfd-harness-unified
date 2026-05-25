/**
 * DEC-V61-205 (M5 C3) · the Post verdict pill must render the REAL
 * comparison verdict or an honest no-baseline state — never the old
 * hardcoded "通过 · +4.2%" PASS. Pure render test (no fetch / no vtk).
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { PostVerdictPill } from "../components/modes/ModeRendererPost";
import type { PostVerdict } from "../hooks/useComparisonVerdict";

const v = (over: Partial<PostVerdict>): PostVerdict => ({
  state: "none",
  level: null,
  detail: null,
  nPass: null,
  nTotal: null,
  ...over,
});

describe("PostVerdictPill (M5 C3 de-fake)", () => {
  it("renders nothing while loading", () => {
    const { container } = render(<PostVerdictPill verdict={v({ state: "loading" })} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders a real PASS with the gold-point count, not a fake gain", () => {
    render(
      <PostVerdictPill
        verdict={v({ state: "verdict", level: "PASS", nPass: 17, nTotal: 17 })}
      />,
    );
    const pill = screen.getByTestId("v4-mode-post-verdict");
    expect(pill.getAttribute("data-verdict")).toBe("pass");
    expect(pill.textContent).toContain("通过 · 对比基准");
    expect(pill.textContent).toContain("17/17 gold 点通过");
    // The old fabricated telemetry must be gone.
    expect(pill.textContent).not.toContain("+4.2%");
    expect(pill.textContent).not.toContain("流量");
  });

  it("renders PARTIAL and FAIL distinctly", () => {
    const { rerender } = render(
      <PostVerdictPill verdict={v({ state: "verdict", level: "PARTIAL", nPass: 14, nTotal: 17 })} />,
    );
    let pill = screen.getByTestId("v4-mode-post-verdict");
    expect(pill.getAttribute("data-verdict")).toBe("partial");
    expect(pill.textContent).toContain("部分通过");

    rerender(
      <PostVerdictPill verdict={v({ state: "verdict", level: "FAIL", nPass: 3, nTotal: 17 })} />,
    );
    pill = screen.getByTestId("v4-mode-post-verdict");
    expect(pill.getAttribute("data-verdict")).toBe("fail");
    expect(pill.textContent).toContain("未通过");
  });

  it("renders an honest no-baseline state (NOT a PASS) when there is no gold reference", () => {
    render(<PostVerdictPill verdict={v({ state: "none" })} />);
    const pill = screen.getByTestId("v4-mode-post-verdict");
    expect(pill.getAttribute("data-verdict")).toBe("none");
    expect(pill.textContent).toContain("无基准对比");
    expect(pill.textContent).not.toContain("通过 · 对比基准");
  });

  it("renders an honest unavailable state on a report-service error", () => {
    render(<PostVerdictPill verdict={v({ state: "error" })} />);
    const pill = screen.getByTestId("v4-mode-post-verdict");
    expect(pill.getAttribute("data-verdict")).toBe("error");
    expect(pill.textContent).toContain("对比报告暂不可用");
  });
});
