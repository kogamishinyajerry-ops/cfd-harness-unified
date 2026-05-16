// Per-component unit tests for TopBar · 6-field information density
// (V67-C.1 · Blueprint v3 §4 alignment).

import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { TopBar } from "../TopBar";

describe("TopBar · 6-field information density (V67-C.1)", () => {
  it("renders caseId in the canonical slot", () => {
    render(<TopBar caseId="imported_2026-04-28T00-00-00Z_demo" />);
    expect(screen.getByTestId("top-bar-case-id")).toHaveTextContent(
      "imported_2026-04-28T00-00-00Z_demo",
    );
  });

  it("defaults saveIndicator to 'idle' / 'ready' when omitted", () => {
    render(<TopBar caseId="abc" />);
    const indicator = screen.getByTestId("save-indicator");
    expect(indicator).toHaveAttribute("data-state", "idle");
    expect(indicator).toHaveTextContent("ready");
  });

  it("maps each saveIndicator value to its label + data-state", () => {
    const cases = [
      { state: "idle" as const, label: "ready" },
      { state: "saving" as const, label: "saving…" },
      { state: "saved" as const, label: "saved" },
      { state: "error" as const, label: "save failed" },
    ];
    for (const { state, label } of cases) {
      const { unmount } = render(
        <TopBar caseId="abc" saveIndicator={state} />,
      );
      const indicator = screen.getByTestId("save-indicator");
      expect(indicator).toHaveAttribute("data-state", state);
      expect(indicator).toHaveTextContent(label);
      unmount();
    }
  });

  it("renders all 6 blueprint fields with defaults", () => {
    render(<TopBar caseId="abc" />);
    // Field 1: case
    expect(screen.getByTestId("top-bar-case-id")).toHaveTextContent("abc");
    // Field 2: OF truth (default "unknown" → "OF —")
    const truth = screen.getByTestId("top-bar-truth-source");
    expect(truth).toHaveAttribute("data-state", "unknown");
    expect(truth).toHaveTextContent("OF —");
    // Field 3: TrustGate (default "PENDING" → "Trust: —")
    const trust = screen.getByTestId("top-bar-trust-gate");
    expect(trust).toHaveAttribute("data-state", "PENDING");
    expect(trust).toHaveTextContent("Trust: —");
    // Field 4: LLM offline (default true → "LLM offline ✓")
    const llm = screen.getByTestId("top-bar-llm-offline");
    expect(llm).toHaveAttribute("data-state", "offline_ok");
    expect(llm).toHaveTextContent("LLM offline ✓");
    // Field 5: Audit % (default null → "Audit —")
    const audit = screen.getByTestId("top-bar-audit-pct");
    expect(audit).toHaveAttribute("data-state", "pending");
    expect(audit).toHaveTextContent("Audit —");
    // Field 6: AI = advisor (constant)
    const ai = screen.getByTestId("top-bar-ai-advisor");
    expect(ai).toHaveAttribute("data-state", "advisor");
    expect(ai).toHaveTextContent("AI = advisor");
  });

  it("renders OF truth in each truthSource variant", () => {
    const variants: Array<["openfoam_native" | "mock" | "unknown", string]> = [
      ["openfoam_native", "OF native"],
      ["mock", "mock"],
      ["unknown", "OF —"],
    ];
    for (const [src, label] of variants) {
      const { unmount } = render(<TopBar caseId="abc" truthSource={src} />);
      const el = screen.getByTestId("top-bar-truth-source");
      expect(el).toHaveAttribute("data-state", src);
      expect(el).toHaveTextContent(label);
      unmount();
    }
  });

  it("renders TrustGate in each variant with correct label", () => {
    const variants: Array<
      ["PASS" | "PASS_WITH_DISCLAIMER" | "FAIL" | "PENDING", string]
    > = [
      ["PASS", "Trust: PASS"],
      ["PASS_WITH_DISCLAIMER", "Trust: PASS*"],
      ["FAIL", "Trust: FAIL"],
      ["PENDING", "Trust: —"],
    ];
    for (const [v, label] of variants) {
      const { unmount } = render(<TopBar caseId="abc" trustGate={v} />);
      const el = screen.getByTestId("top-bar-trust-gate");
      expect(el).toHaveAttribute("data-state", v);
      expect(el).toHaveTextContent(label);
      unmount();
    }
  });

  it("renders LLM offline=false as 'LLM online' with online state", () => {
    render(<TopBar caseId="abc" llmOffline={false} />);
    const el = screen.getByTestId("top-bar-llm-offline");
    expect(el).toHaveAttribute("data-state", "online");
    expect(el).toHaveTextContent("LLM online");
  });

  it("formats audit% correctly in 3 tone bands", () => {
    const cases: Array<[number | null, string, string]> = [
      [95, "computed", "Audit 95%"],
      [70, "computed", "Audit 70%"],
      [30, "computed", "Audit 30%"],
      [null, "pending", "Audit —"],
    ];
    for (const [pct, state, label] of cases) {
      const { unmount } = render(<TopBar caseId="abc" auditPct={pct} />);
      const el = screen.getByTestId("top-bar-audit-pct");
      expect(el).toHaveAttribute("data-state", state);
      expect(el).toHaveTextContent(label);
      unmount();
    }
  });

  it("renders AI = advisor as a static badge regardless of other props", () => {
    render(<TopBar caseId="abc" trustGate="FAIL" llmOffline={false} />);
    const ai = screen.getByTestId("top-bar-ai-advisor");
    expect(ai).toHaveTextContent("AI = advisor");
    expect(ai).toHaveAttribute("data-state", "advisor");
  });
});
