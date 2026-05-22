// DEC-V61-202-SUB-M30-CYCLE1 · DynamicBottomCards tests.

import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { DynamicBottomCards } from "../DynamicBottomCards";
import type { BottomCard } from "@/types/workbench_frame";

describe("DynamicBottomCards", () => {
  it("renders nothing when cards array is empty", () => {
    const { container } = render(<DynamicBottomCards cards={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders an audit_finding card with severity tone + source artifact", () => {
    const cards: BottomCard[] = [
      {
        kind: "audit_finding",
        title: "missing field p_rgh",
        body_text: "interFoam expects 0/p_rgh; not found on disk",
        severity: "fail",
        source_artifact: "bc_quality.json",
        field_path: "bc_contract.pressure",
      },
    ];
    render(<DynamicBottomCards cards={cards} />);
    const card = screen.getByTestId("bottom-card");
    expect(card.dataset.kind).toBe("audit_finding");
    expect(card.dataset.severity).toBe("fail");
    expect(screen.getByText("missing field p_rgh")).toBeInTheDocument();
    expect(
      screen.getByText("interFoam expects 0/p_rgh; not found on disk"),
    ).toBeInTheDocument();
    expect(screen.getByText("审计发现")).toBeInTheDocument();
    expect(screen.getByText(/bc_quality\.json/)).toBeInTheDocument();
  });

  it("renders a missing_field card", () => {
    const cards: BottomCard[] = [
      {
        kind: "missing_field",
        title: "缺字段 / Missing: vof_contract.phases",
        body_text: "interFoam requires phases declaration",
        severity: "warn",
        source_artifact: "completeness_report",
        field_path: "vof_contract.phases",
      },
    ];
    render(<DynamicBottomCards cards={cards} />);
    expect(screen.getByText("缺字段")).toBeInTheDocument();
    const card = screen.getByTestId("bottom-card");
    expect(card.dataset.severity).toBe("warn");
  });

  it("renders a step_hint card when no findings", () => {
    const cards: BottomCard[] = [
      {
        kind: "step_hint",
        title: "Step 4 · 边界条件 / BCs",
        body_text: "为每个面设置 BC 类型 + 数值；engine 会比对 expected_fields。",
        severity: "info",
        source_artifact: null,
        field_path: null,
      },
    ];
    render(<DynamicBottomCards cards={cards} />);
    expect(screen.getByText("本步提示")).toBeInTheDocument();
    expect(
      screen.getByText("Step 4 · 边界条件 / BCs"),
    ).toBeInTheDocument();
  });

  it("renders multiple cards sorted as given", () => {
    const cards: BottomCard[] = [
      {
        kind: "audit_finding",
        title: "fail-A",
        body_text: "",
        severity: "fail",
        source_artifact: null,
        field_path: null,
      },
      {
        kind: "audit_finding",
        title: "warn-B",
        body_text: "",
        severity: "warn",
        source_artifact: null,
        field_path: null,
      },
    ];
    render(<DynamicBottomCards cards={cards} />);
    const all = screen.getAllByTestId("bottom-card");
    expect(all).toHaveLength(2);
    expect(all[0]).toHaveTextContent("fail-A");
    expect(all[1]).toHaveTextContent("warn-B");
  });

  it("omits footer when no field_path + no source_artifact", () => {
    const cards: BottomCard[] = [
      {
        kind: "step_hint",
        title: "static hint",
        body_text: "hint text",
        severity: "info",
        source_artifact: null,
        field_path: null,
      },
    ];
    const { container } = render(<DynamicBottomCards cards={cards} />);
    expect(container.querySelectorAll("footer")).toHaveLength(0);
  });
});
