// Round-2 Q15 minimum smoke + Tier-B(2) SSE state-machine coverage.
// Mocks EventSource so tests can dispatch crafted events and assert
// that phase state transitions are wired correctly. Round-3 review
// flagged this surface as 0-test; ~600 LOC of TSX with EventSource
// lifecycle silently breaking on response shape changes.
import { act } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { WorkbenchRunPage } from "../WorkbenchRunPage";

// Track the live EventSource instance so tests can drive onmessage.
let _activeES: MockEventSource | null = null;

class MockEventSource {
  url: string;
  onmessage: ((m: MessageEvent) => void) | null = null;
  onerror: ((e: Event) => void) | null = null;
  constructor(url: string) {
    this.url = url;
    _activeES = this;
  }
  close() {
    _activeES = null;
  }
  // Test helper: dispatch a JSON event as if SSE delivered it.
  __emit(payload: unknown) {
    if (this.onmessage) {
      this.onmessage(
        new MessageEvent("message", { data: JSON.stringify(payload) }),
      );
    }
  }
}

vi.stubGlobal("EventSource", MockEventSource as unknown as typeof EventSource);

function emit(payload: unknown) {
  if (!_activeES) throw new Error("no active EventSource");
  act(() => {
    _activeES!.__emit(payload);
  });
}

function renderPage(caseId: string) {
  return render(
    <MemoryRouter initialEntries={[`/workbench/run/${caseId}`]}>
      <Routes>
        <Route path="/workbench/run/:caseId" element={<WorkbenchRunPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("WorkbenchRunPage · smoke", () => {
  it("renders without crash and shows the case_id", () => {
    renderPage("smoke_test_case");
    expect(screen.getByText("smoke_test_case")).toBeInTheDocument();
  });

  it("shows all 5 phases in the stepper at mount time", () => {
    renderPage("smoke_test_case");
    // Each Chinese label appears twice (stepper grid + phase panel header)
    // so we use getAllByText and assert >= 1 instance per phase. Each phase
    // also has its English id present once in the stepper as a code-style
    // glyph — that's the unique anchor per phase.
    for (const label of [
      /几何与边界/,
      /网格生成/,
      /边界条件/,
      /求解器迭代/,
      /对照黄金标准/,
    ]) {
      expect(screen.getAllByText(label).length).toBeGreaterThanOrEqual(1);
    }
  });
});

describe("WorkbenchRunPage · SSE state machine (Tier-B(2))", () => {
  it("phase_start flips status from pending to running", () => {
    renderPage("test_case");
    // Initial: all phases pending
    expect(screen.getAllByText("待执行").length).toBeGreaterThanOrEqual(5);
    expect(screen.queryByText("执行中")).not.toBeInTheDocument();

    emit({
      type: "phase_start",
      phase: "geometry",
      t: 1.0,
      message: "正在生成几何...",
    });
    expect(screen.getByText("执行中")).toBeInTheDocument();
  });

  it("phase_done flips status to ok and shows summary", () => {
    renderPage("test_case");
    emit({ type: "phase_start", phase: "mesh", t: 1.0 });
    emit({
      type: "phase_done",
      phase: "mesh",
      t: 2.0,
      status: "ok",
      summary: "mesh OK · 1600 cells · skew 1e-15",
    });
    expect(screen.getByText("完成")).toBeInTheDocument();
    expect(screen.getByText(/mesh OK · 1600 cells/)).toBeInTheDocument();
  });

  it("log events accumulate in the active phase panel", () => {
    renderPage("test_case");
    emit({ type: "phase_start", phase: "solver", t: 1.0 });
    emit({ type: "log", phase: "solver", t: 1.1, line: "Time = 0.01s" });
    emit({ type: "log", phase: "solver", t: 1.2, line: "Time = 0.05s" });
    emit({ type: "log", phase: "solver", t: 1.3, line: "Time = 0.10s" });
    expect(screen.getByText(/Time = 0\.01s/)).toBeInTheDocument();
    expect(screen.getByText(/Time = 0\.05s/)).toBeInTheDocument();
    expect(screen.getByText(/Time = 0\.10s/)).toBeInTheDocument();
  });

  it("metric events render as residual chips on solver phase", () => {
    renderPage("test_case");
    emit({ type: "phase_start", phase: "solver", t: 1.0 });
    emit({
      type: "metric",
      phase: "solver",
      t: 1.1,
      metric_key: "residual_p",
      metric_value: 1.2e-3,
    });
    expect(screen.getByText(/residual_p=1\.20e-3/i)).toBeInTheDocument();
  });

  it("phase_done with status fail flips to fail glyph", () => {
    renderPage("test_case");
    emit({ type: "phase_start", phase: "compare", t: 1.0 });
    emit({
      type: "phase_done",
      phase: "compare",
      t: 2.0,
      status: "fail",
      summary: "compare FAIL · max deviation 31%",
    });
    expect(screen.getByText("失败")).toBeInTheDocument();
  });

  it("run_done shows the next-steps card with edit / new-case links", () => {
    renderPage("my_demo_case");
    // Walk through 5 phases to completion
    for (const phase of ["geometry", "mesh", "boundary", "solver", "compare"]) {
      emit({ type: "phase_start", phase, t: 1.0 });
      emit({ type: "phase_done", phase, t: 2.0, status: "ok", summary: "ok" });
    }
    emit({
      type: "run_done",
      t: 3.0,
      summary: "run complete · case_id=my_demo_case · 5 phases OK",
    });
    expect(screen.getByText(/下一步/)).toBeInTheDocument();
    // Round-2 navigation hooks: edit + new-case links exist
    const editLink = screen.getByRole("link", { name: /YAML 编辑器/ });
    expect(editLink).toHaveAttribute(
      "href",
      "/cases/my_demo_case/edit",
    );
    const newLink = screen.getByRole("link", { name: /再建一个新案例/ });
    expect(newLink).toHaveAttribute("href", "/workbench/new");
  });
});
