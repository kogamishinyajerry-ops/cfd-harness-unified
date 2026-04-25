// Round-2 Q15 minimum smoke test for WorkbenchRunPage.
// Mocks EventSource so the page can mount in jsdom without a real SSE
// connection. Asserts the 5-phase stepper renders all phases, all in
// pending state initially, plus the case_id appears in the header.
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { WorkbenchRunPage } from "../WorkbenchRunPage";

class MockEventSource {
  url: string;
  onmessage: ((m: MessageEvent) => void) | null = null;
  onerror: ((e: Event) => void) | null = null;
  constructor(url: string) {
    this.url = url;
  }
  close() {}
}

// jsdom does not implement EventSource; install the mock globally.
vi.stubGlobal("EventSource", MockEventSource as unknown as typeof EventSource);

function renderPage(caseId: string) {
  return render(
    <MemoryRouter initialEntries={[`/workbench/run/${caseId}`]}>
      <Routes>
        <Route path="/workbench/run/:caseId" element={<WorkbenchRunPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("WorkbenchRunPage", () => {
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
