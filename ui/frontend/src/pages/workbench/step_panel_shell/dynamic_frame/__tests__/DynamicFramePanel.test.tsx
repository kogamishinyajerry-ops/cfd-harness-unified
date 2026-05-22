// DEC-V61-202-SUB-M30-CYCLE1 · DynamicFramePanel tests.
//
// Coverage: tone selection per kind, body_text + field_path rendering,
// CTA visibility, provenance disclosure toggle, empty-body fallback.

import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { DynamicFramePanel } from "../DynamicFramePanel";
import type { RailPrimary } from "@/types/workbench_frame";

const PROBLEM_RAIL: RailPrimary = {
  kind: "problem_fix",
  title: "BC fields missing",
  body_text: "interFoam expects 0/p_rgh; not found on disk",
  field_path: "bc_contract.pressure",
  suggested_default: null,
  cta_label: "查看 / View",
  provenance: [
    "step=4 · problem_fix · severity=fail",
    "source=bc_quality.json",
  ],
};

const GAP_RAIL: RailPrimary = {
  kind: "info_gap",
  title: "补充字段 / Fill: vof_contract.phases",
  body_text: "interFoam case requires vof_contract.phases",
  field_path: "vof_contract.phases",
  suggested_default: ["water", "air"],
  cta_label: "填入 / Apply",
  provenance: ["step=3 · info_gap · severity=critical"],
};

const DEFAULT_RAIL: RailPrimary = {
  kind: "step_default",
  title: "Step 3 · 物理已设 / Physics set",
  body_text: "当前步无阻塞 — 可以进入下一步。",
  field_path: null,
  suggested_default: null,
  cta_label: "下一步 / Next",
  provenance: ["step=3 · step_default · no blockers"],
};

describe("DynamicFramePanel", () => {
  it("renders problem_fix kind with rose-toned label", () => {
    render(<DynamicFramePanel rail={PROBLEM_RAIL} />);
    const panel = screen.getByTestId("dynamic-frame-panel");
    expect(panel.dataset.kind).toBe("problem_fix");
    expect(screen.getByText("需修复")).toBeInTheDocument();
    expect(screen.getByText("BC fields missing")).toBeInTheDocument();
    expect(screen.getByText(/interFoam expects 0\/p_rgh/)).toBeInTheDocument();
    expect(screen.getByText("bc_contract.pressure")).toBeInTheDocument();
  });

  it("renders info_gap kind with amber label + CTA", () => {
    render(<DynamicFramePanel rail={GAP_RAIL} />);
    expect(screen.getByText("待补充")).toBeInTheDocument();
    expect(
      screen.getByText("补充字段 / Fill: vof_contract.phases"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("dynamic-frame-cta")).toHaveTextContent(
      "填入 / Apply",
    );
  });

  it("renders step_default kind with emerald label", () => {
    render(<DynamicFramePanel rail={DEFAULT_RAIL} />);
    expect(screen.getByText("就绪")).toBeInTheDocument();
    expect(
      screen.getByText("Step 3 · 物理已设 / Physics set"),
    ).toBeInTheDocument();
  });

  it("toggles provenance disclosure on click", async () => {
    render(<DynamicFramePanel rail={PROBLEM_RAIL} />);
    // Collapsed by default.
    expect(
      screen.queryByText("step=4 · problem_fix · severity=fail"),
    ).not.toBeInTheDocument();
    await userEvent.click(screen.getByText("▸ 为什么显示这个"));
    expect(
      screen.getByText("step=4 · problem_fix · severity=fail"),
    ).toBeInTheDocument();
  });

  it("omits body section when body_text is null", () => {
    const noBody: RailPrimary = { ...DEFAULT_RAIL, body_text: null };
    render(<DynamicFramePanel rail={noBody} />);
    expect(screen.getByText(DEFAULT_RAIL.title)).toBeInTheDocument();
    expect(
      screen.queryByText("当前步无阻塞 — 可以进入下一步。"),
    ).not.toBeInTheDocument();
  });
});
